"""网易云息屏歌词 —— 数据层。

职责：
1. 通过读取网易云主窗口标题（"歌名 - 歌手"）获取当前播放歌曲；
2. 通过网易云调试端口(CDP)读取真实播放进度（解决切歌/暂停/回退的对时）；
3. 通过网易云音乐公开接口搜索并下载歌词（含翻译）；
4. 解析 LRC 时间轴并定位当前歌词行。

进度来源优先级：CDP（精确）→ 本地计时器（近似回退）。
"""

import ctypes
import json
import os
import re
import subprocess
import threading
import time
import urllib.request
from ctypes import wintypes
from typing import List, Optional, Tuple

import requests
import websocket

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 网易云调试端口（用 `cloudmusic.exe --remote-debugging-port=9223` 启动时可用）
CDP_PORT = 9223

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")
HEADERS = {"Referer": "https://music.163.com", "User-Agent": UA}

META_KEYWORDS = (
    "作词", "作曲", "编曲", "制作人", "制作", "录音", "混音", "母带",
    "和声", "吉他", "贝斯", "鼓", "键盘", "弦乐", "监制", "出品", "发行",
    "纯音乐", "暂无歌词", "歌词制作", "歌词整理", "上传", "LRC", "lrc",
    "Timeline", "歌手", "专辑", "唱片", "版本", "未经授权", "版权所有",
    "词曲", "演唱", "OP", "SP",
)

CJK_RE = re.compile(r"[一-鿿]")
TIMESTAMP_RE = re.compile(r"\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]")

COVER_MARKERS = (
    "版", "cover", "翻唱", "翻录", "原唱", "remix", "live", "伴奏", "instrumental",
    "dj", "remaster", "钢琴", "吉他", "古筝", "葫芦丝", "现场", "童声", "女声",
    "男声", "纯音乐", "轻音乐", "demo", "片段", "铃声", "合唱", "重制", "深情",
    "治愈", "正式", "变速", "降调", "升调", "混音",
)


# --------------------------------------------------------------------------
# LRC 解析
# --------------------------------------------------------------------------
def _is_metadata(text: str) -> bool:
    t = text.strip()
    if not t:
        return True
    if re.match(r"^[^-]{1,40}\s+-\s+[^-]{1,40}$", t):
        return True
    for kw in META_KEYWORDS:
        if kw in t:
            return True
    return False


def parse_lrc(lrc_text: str) -> List[Tuple[float, str]]:
    result: List[Tuple[float, str]] = []
    for raw in lrc_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        matches = list(TIMESTAMP_RE.finditer(line))
        if not matches:
            continue
        content = line[matches[-1].end():].strip()
        if _is_metadata(content):
            continue
        for m in matches:
            mm = int(m.group(1))
            ss = int(m.group(2))
            frac = m.group(3) or "0"
            frac = int(frac.ljust(3, "0")[:3])
            t = mm * 60 + ss + frac / 1000.0
            result.append((t, content))
    result.sort(key=lambda x: x[0])
    return result


def detect_mode(lines: List[Tuple[float, str]]) -> str:
    text = "".join(content for _, content in lines)
    total = len([c for c in text if not c.isspace()])
    if total == 0:
        return "chinese"
    cjk = len(CJK_RE.findall(text))
    return "chinese" if cjk / total >= 0.3 else "nonchinese"


def align_translations(lines, tlines) -> List[Tuple[float, str, str]]:
    trans_by_time = {}
    for tt, txt in tlines:
        trans_by_time.setdefault(round(tt, 2), txt)
    out = []
    for t, text in lines:
        key = round(t, 2)
        tr = trans_by_time.get(key)
        if tr is None:
            best, best_d = "", 1e9
            for tt, txt in tlines:
                d = abs(tt - t)
                if d < best_d and d <= 0.6:
                    best_d, best = d, txt
            tr = best
        out.append((t, text, tr or ""))
    return out


# --------------------------------------------------------------------------
# 网易云搜索与歌词下载
# --------------------------------------------------------------------------
def _norm(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[\(（\[【].*?[\)）\]】]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _title_score(query: str, result: str) -> float:
    a = query.strip().lower()
    b = result.strip().lower()
    if not a or not b:
        return 0.0
    if a == b:
        return 2.0
    na, nb = _norm(a), _norm(b)
    if na == nb:
        return 0.6
    if na and nb and (na in nb or nb in na):
        return 0.3
    return 0.0


def _artist_score(query: str, result: str) -> float:
    a = query.strip().lower()
    b = result.strip().lower()
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.8
    ta = set(re.split(r"[/&·、,]+", a))
    tb = set(re.split(r"[/&·、,]+", b))
    if ta & tb:
        return 0.7
    return 0.0


def _has_bracket(s: str) -> bool:
    return bool(re.search(r"[\(（\[【]", s))


def _has_cover_marker(s: str) -> bool:
    t = s.lower()
    return any(m in t for m in COVER_MARKERS)


# 搜索限流：避免网易云接口返回 405（请求过于频繁）
_search_lock = threading.Lock()
_last_search_mono = 0.0
SEARCH_MIN_INTERVAL = 0.6

SEARCH_ENDPOINTS = (
    "https://music.163.com/api/search/get",       # 旧接口，稳定、不限流
    "https://music.163.com/api/search/get/web",   # 新接口，高频时可能 405
)


def _rate_limited_get(url: str, params: dict, timeout: float = 15):
    global _last_search_mono
    with _search_lock:
        wait = SEARCH_MIN_INTERVAL - (time.monotonic() - _last_search_mono)
        if wait > 0:
            time.sleep(wait)
        r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        _last_search_mono = time.monotonic()
    return r


def search_songs(query: str, limit: int = 12) -> List[dict]:
    """搜索歌曲，多端点回退 + 限流 + 重试。"""
    params = {"s": query, "type": 1, "limit": limit, "offset": 0}
    for attempt in range(3):
        for url in SEARCH_ENDPOINTS:
            try:
                d = _rate_limited_get(url, params).json()
                if d.get("code") == 405:
                    continue
                songs = (d.get("result") or {}).get("songs") or []
                if songs:
                    return songs
            except Exception:
                continue
        time.sleep(1.2 * (attempt + 1))
    return []


def search_best(title: str, artist: str, limit: int = 12) -> Optional[dict]:
    q = f"{title} {artist}".strip()
    if not q:
        return None
    songs = search_songs(q, limit)
    best, best_score = None, -1e9
    for i, s in enumerate(songs):
        st = s.get("name") or ""
        sa = " ".join((a.get("name") or "") for a in (s.get("artists") or []))
        score = _title_score(title, st) + _artist_score(artist, sa) * 0.4
        if _has_cover_marker(st):
            score -= 0.8
        if _has_bracket(st):
            score -= 0.3
        score += (limit - i) * 0.01
        if score > best_score:
            best_score, best = score, s
    return best


def fetch_lyric(song_id: int) -> Tuple[str, str]:
    r = requests.get(
        "https://music.163.com/api/song/lyric",
        params={"id": song_id, "lv": -1, "kv": -1, "tv": -1},
        headers=HEADERS, timeout=15,
    )
    r.raise_for_status()
    d = r.json()
    lrc = (d.get("lrc") or {}).get("lyric") or ""
    tlyric = (d.get("tlyric") or {}).get("lyric") or ""
    return lrc, tlyric


# --------------------------------------------------------------------------
# 网易云窗口标题读取（"歌名 - 歌手"）
# --------------------------------------------------------------------------
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

_TITLE_SEPS = (" - ", " – ", " — ")


def _get_window_text(hwnd: int) -> str:
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def _process_name(pid: int) -> str:
    try:
        h = kernel32.OpenProcess(0x1000, False, pid)
        if not h:
            return ""
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        ok = kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
        kernel32.CloseHandle(h)
        return buf.value if ok else ""
    except Exception:
        return ""


def _find_song_title() -> str:
    hwnd = user32.FindWindowW("OrpheusBrowserHost", None)
    if hwnd:
        title = _get_window_text(hwnd)
        if " - " in title:
            return title
    result: List[str] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _lparam):
        title = _get_window_text(hwnd)
        if " - " not in title:
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if cls.value == "OrpheusBrowserHost" or _process_name(pid.value).lower().endswith("cloudmusic.exe"):
            result.append(title)
        return True

    user32.EnumWindows(cb, 0)
    return result[0] if result else ""


def parse_song_title(full: str) -> Optional[Tuple[str, str]]:
    full = (full or "").strip()
    if not full:
        return None
    for sep in _TITLE_SEPS:
        if sep in full:
            i = full.rfind(sep)
            title = full[:i].strip()
            artist = full[i + len(sep):].strip()
            if title and artist:
                return title, artist
    return None


class NetEaseWindowReader:
    """后台线程持续读取网易云窗口标题。"""

    def __init__(self, interval: float = 0.7):
        self._lock = threading.Lock()
        self._latest: Optional[dict] = None
        self._stop = threading.Event()
        self._interval = interval

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while not self._stop.is_set():
            try:
                parsed = parse_song_title(_find_song_title())
                data = {"title": parsed[0], "artist": parsed[1]} if parsed else None
            except Exception:
                data = None
            with self._lock:
                self._latest = data
            self._stop.wait(self._interval)

    def get(self) -> Optional[dict]:
        with self._lock:
            return self._latest

    def stop(self):
        self._stop.set()


# --------------------------------------------------------------------------
# 网易云调试端口(CDP) 读取真实播放进度
# --------------------------------------------------------------------------
_POSITION_JS = r"""
(function(){
  function parse(t){
    var m = t.match(/(\d{1,3}):(\d{2})\s*\/\s*(\d{1,3}):(\d{2})/);
    if(!m) return null;
    return {cur: (+m[1])*60 + (+m[2]), total: (+m[3])*60 + (+m[4])};
  }
  var out = {cur: null, total: null, songId: null};

  // 1) 精确进度：播放进度条内部隐藏的 range input（毫秒级，如 value=69.006）
  var sl = document.querySelector('[class*="slider-default"], [class*="slider-vinyl"]');
  var inp = sl ? sl.querySelector('input[type="range"]') : null;
  if (inp) {
    var v = parseFloat(inp.value), mx = parseFloat(inp.max);
    if (!isNaN(v) && !isNaN(mx) && mx > 0) { out.cur = v; out.total = mx; }
  }

  // 2) 回退：界面上的 "MM:SS / MM:SS" 文本
  if (out.cur === null) {
    var el = document.querySelector('[class*="curtime-thumb"]');
    if (el) { var p = parse((el.textContent||'').trim()); if (p) { out.cur = p.cur; out.total = p.total; } }
  }
  if (out.cur === null) {
    var els = document.querySelectorAll('*');
    for (var i=0;i<els.length;i++){
      var t = (els[i].textContent||'').trim();
      if (t.length > 40) continue;
      var q = parse(t);
      if (q && els[i].children.length <= 3) { out.cur = q.cur; out.total = q.total; break; }
    }
  }

  // 3) 当前歌曲 ID
  var bar = document.getElementById('page_pc_mini_bar');
  if (bar) {
    try {
      var d = JSON.parse(bar.getAttribute('data-log'));
      if (d && d.params && d.params.s_cid) out.songId = String(d.params.s_cid);
    } catch(e) {}
  }
  if (out.cur === null && out.songId === null) return null;
  return out;
})()
"""


class NetEaseCdpReader:
    """通过 CDP 读取播放进度，返回 {"cur": 秒, "total": 秒, "moving": 是否在前进}。"""

    def __init__(self, port: int = CDP_PORT, interval: float = 0.5):
        self._port = port
        self._interval = interval
        self._lock = threading.Lock()
        self._latest: Optional[dict] = None
        self._stop = threading.Event()
        self._ws = None
        self._msg_id = 0
        self._prev_cur: Optional[float] = None
        self._prev_song: Optional[str] = None

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _connect(self):
        targets = json.load(
            urllib.request.urlopen(f"http://127.0.0.1:{self._port}/json/list", timeout=3))
        page = next((t for t in targets if t.get("type") == "page"), None)
        if not page:
            return None
        return websocket.create_connection(page["webSocketDebuggerUrl"], timeout=5)

    def _run(self):
        while not self._stop.is_set():
            try:
                if self._ws is None:
                    self._ws = self._connect()
                if self._ws is not None:
                    cur, total, song_id = self._read_position()
                    moving = False
                    if song_id and self._prev_song and song_id != self._prev_song:
                        # 切歌：新歌视为正在播放
                        moving = True
                        self._prev_cur = None
                    if song_id:
                        self._prev_song = song_id
                    if cur is not None:
                        if self._prev_cur is not None and cur > self._prev_cur + 0.05:
                            moving = True
                        self._prev_cur = cur
                    with self._lock:
                        self._latest = ({"cur": cur, "total": total,
                                         "moving": moving, "songId": song_id}
                                        if (cur is not None or song_id) else None)
                else:
                    with self._lock:
                        self._latest = None
            except Exception:
                with self._lock:
                    self._latest = None
                try:
                    if self._ws:
                        self._ws.close()
                except Exception:
                    pass
                self._ws = None
            self._stop.wait(self._interval)

    def _read_position(self) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        self._msg_id += 1
        self._ws.send(json.dumps({
            "id": self._msg_id, "method": "Runtime.evaluate",
            "params": {"expression": _POSITION_JS, "returnByValue": True},
        }))
        while True:
            m = json.loads(self._ws.recv())
            if m.get("id") == self._msg_id:
                val = (m.get("result") or {}).get("result", {}).get("value")
                if isinstance(val, dict):
                    cur = val.get("cur")
                    total = val.get("total")
                    song_id = val.get("songId")
                    return (float(cur) if cur is not None else None,
                            float(total) if total is not None else None,
                            str(song_id) if song_id else None)
                return None, None, None

    def get(self) -> Optional[dict]:
        with self._lock:
            return self._latest

    def stop(self):
        self._stop.set()
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass


# --------------------------------------------------------------------------
# 网易云启动辅助（带调试端口，用于精确同步）
# --------------------------------------------------------------------------
def _cloudmusic_process_pids() -> List[int]:
    try:
        out = subprocess.run(["tasklist"], capture_output=True, text=True,
                             errors="replace", timeout=5).stdout
        return [int(l.split()[1]) for l in out.splitlines()
                if "cloudmusic.exe" in l.lower() and len(l.split()) >= 2]
    except Exception:
        return []


def find_cloudmusic_exe() -> Optional[str]:
    """返回 cloudmusic.exe 的完整路径。"""
    for pid in _cloudmusic_process_pids():
        try:
            h = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                continue
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                kernel32.CloseHandle(h)
                return buf.value
            kernel32.CloseHandle(h)
        except Exception:
            continue
    for p in (
        r"D:\Program Files\NetEase\CloudMusic\cloudmusic.exe",
        r"C:\Program Files (x86)\NetEase\CloudMusic\cloudmusic.exe",
        r"C:\Program Files\NetEase\CloudMusic\cloudmusic.exe",
    ):
        if os.path.exists(p):
            return p
    return None


def restart_netease_debug(port: int = CDP_PORT) -> bool:
    """以 `--remote-debugging-port` 重启网易云，用于歌词精确同步。"""
    exe = find_cloudmusic_exe()
    if not exe:
        return False
    try:
        subprocess.run(["taskkill", "/F", "/IM", "cloudmusic.exe"],
                       capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        subprocess.run(["taskkill", "/F", "/IM", "cloudmusic_reporter.exe"],
                       capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        pass
    time.sleep(1.5)
    try:
        subprocess.Popen(
            [exe, f"--remote-debugging-port={port}"],
            cwd=os.path.dirname(exe),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------
# 歌词提供器
# --------------------------------------------------------------------------
class LyricProvider:
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0

    def __init__(self):
        self.reader = NetEaseWindowReader(interval=0.2)
        self.cdp = NetEaseCdpReader(interval=0.1)
        self._lock = threading.RLock()
        self._lines_key: Optional[str] = None   # 当前歌词所属的歌曲
        self._lines: List[Tuple[float, str, str]] = []
        self._mode = "chinese"
        self._fetching = False
        self._fetch_key: Optional[str] = None
        self._error: Optional[str] = None
        self._cache: dict = {}                  # key -> (lines, mode)
        self._retries: dict = {}                # key -> [下次重试 monotonic, 已重试次数]
        # 进度插值：采样点 + 播放速率 + 活跃截止时间
        self._cdp_cur: Optional[float] = None
        self._cdp_mono = 0.0
        self._cdp_rate = 1.0
        self._cdp_active_until = 0.0
        # 计时器回退用
        self._play_key: Optional[str] = None
        self._start_mono = 0.0
        self._last_move_mono = 0.0

    def start(self):
        self.reader.start()
        self.cdp.start()

    def stop(self):
        self.reader.stop()
        self.cdp.stop()

    @staticmethod
    def _make_key(title: str, artist: str, song_id: Optional[str]) -> Optional[str]:
        if song_id:
            return f"id:{song_id}"
        if title:
            return f"{title}|{artist}"
        return None

    def get_state(self) -> dict:
        now = time.monotonic()
        snap = self.reader.get()
        cdp = self.cdp.get()

        with self._lock:
            title, artist = "", ""
            if snap:
                title = snap.get("title") or ""
                artist = snap.get("artist") or ""
            song_id = cdp.get("songId") if cdp else None
            has_song = bool(title or song_id)
            key = self._make_key(title, artist, song_id)

            if key is not None and key != self._lines_key and key != self._fetch_key:
                retry = self._retries.get(key)
                due = retry is None or now >= retry[0]
                exhausted = retry is not None and retry[1] > self.MAX_RETRIES
                if due and not exhausted:
                    self._start_fetch(key, title, artist, song_id)

            # 位置：优先 CDP 精确进度（采样 + 本地插值），否则计时器估算
            if cdp is not None and cdp.get("cur") is not None:
                cur = float(cdp["cur"])
                if self._cdp_cur is None or abs(cur - self._cdp_cur) > 1e-4:
                    # 新采样：估计播放速率（倍速时 >1），并刷新活跃时间
                    if self._cdp_cur is not None:
                        dt = now - self._cdp_mono
                        dp = cur - self._cdp_cur
                        if dt > 0.05 and dp > 0.01:
                            inst = dp / dt
                            if 0.2 <= inst <= 4.0:
                                self._cdp_rate = self._cdp_rate * 0.6 + inst * 0.4
                    self._cdp_cur = cur
                    self._cdp_mono = now
                    if cdp.get("moving"):
                        # 网易云界面约每 0.94 秒刷新一次，1.4 秒无增长视为暂停
                        self._cdp_active_until = now + 1.4
                active = now < self._cdp_active_until
                if active:
                    current_pos = self._cdp_cur + (now - self._cdp_mono) * self._cdp_rate
                    playing = True
                else:
                    current_pos = self._cdp_cur
                    playing = False
            else:
                if key:
                    if key != self._play_key:
                        self._play_key = key
                        self._start_mono = now
                else:
                    self._play_key = None
                    self._start_mono = now
                current_pos = (now - self._start_mono) if (key and self._play_key) else 0.0
                playing = has_song

            # 只有歌词确实属于当前歌曲时才使用，避免切歌时短暂沿用上一首的歌词
            own_lines = self._lines if (key is not None and self._lines_key == key) else []

            # 计算当前行
            idx = -1
            for i, (t, _text, _tr) in enumerate(own_lines):
                if t <= current_pos:
                    idx = i
                else:
                    break

            if not has_song:
                status = "no_song"
            elif not own_lines:
                retry = self._retries.get(key) if key else None
                retrying = retry is not None and retry[1] <= self.MAX_RETRIES
                if self._fetching or key == self._fetch_key or retrying:
                    status = "loading"
                else:
                    status = "no_lyrics"
            elif not playing:
                status = "paused"
            else:
                status = "playing"

            return {
                "status": status,
                "title": title,
                "artist": artist,
                "playing": playing,
                "mode": self._mode,
                "current": idx,
                "position": round(current_pos, 2),
                "error": self._error,
                "cdp": cdp is not None,
                "lines": [{"time": round(t, 2), "text": text, "trans": tr}
                          for t, text, tr in own_lines],
            }

    def _start_fetch(self, key: str, title: str, artist: str,
                     song_id: Optional[str]):
        cached = self._cache.get(key)
        if cached is not None:
            # 命中缓存：秒切
            lines, mode = cached
            self._lines_key = key
            self._lines = lines
            self._mode = mode
            self._error = None
            self._fetching = False
            self._fetch_key = None
            self._retries.pop(key, None)
            return
        self._fetching = True
        self._fetch_key = key
        threading.Thread(target=self._fetch_worker,
                         args=(key, title, artist, song_id), daemon=True).start()

    def _fetch_worker(self, key: str, title: str, artist: str,
                      song_id: Optional[str]):
        lines, mode, error = [], "chinese", None
        permanent = False
        try:
            if song_id:
                # 有 CDP 歌曲 ID 时直接取歌词：一次请求，最快且版本准确
                lrc, tlyric = fetch_lyric(int(song_id))
            else:
                song = search_best(title, artist)
                if not song:
                    raise RuntimeError("未找到匹配的歌曲")
                lrc, tlyric = fetch_lyric(song["id"])
            plines = parse_lrc(lrc)
            if not plines:
                permanent = True
                raise RuntimeError("该歌曲没有歌词")
            mode = detect_mode(plines)
            tlines = parse_lrc(tlyric) if tlyric else []
            lines = align_translations(plines, tlines)
            if lines:
                self._cache[key] = (lines, mode)
        except Exception as e:  # noqa: BLE001
            error = str(e)

        with self._lock:
            # 只有当用户仍在播放这首歌时才应用结果
            if self._fetch_key == key:
                self._fetching = False
                self._fetch_key = None
                if lines:
                    self._lines_key = key
                    self._lines = lines
                    self._mode = mode
                    self._error = None
                    self._retries.pop(key, None)
                else:
                    self._error = error
                    if permanent:
                        # 确定没有歌词，不必重试
                        self._retries[key] = [float("inf"), self.MAX_RETRIES + 1]
                    else:
                        # 偶发失败：安排自动重试
                        prev = self._retries.get(key)
                        count = (prev[1] if prev else 0) + 1
                        self._retries[key] = [time.monotonic() + self.RETRY_DELAY, count]
