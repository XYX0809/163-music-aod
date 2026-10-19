# 163 Music AOD · 完整项目文档

<p>
  <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg">
  <img alt="Python" src="https://img.shields.io/badge/Python-58.1%25-3572A5?logo=python&logoColor=white">
  <img alt="HTML" src="https://img.shields.io/badge/HTML-33.5%25-E34C26?logo=html5&logoColor=white">
  <img alt="CSS" src="https://img.shields.io/badge/CSS-7.8%25-563D7C?logo=css3&logoColor=white">
  <img alt="Batch" src="https://img.shields.io/badge/Batch-0.7%25-C1F12E">
</p>
<p>
  <img alt="Made with DeepSeek V4.1 Flash" src="https://img.shields.io/badge/Made%20with-DeepSeek%20V4.1%20Flash-6F42C1">
  <img alt="Authors: XYX0809 & BA4IHB" src="https://img.shields.io/badge/Authors-XYX0809%20%26%20BA4IHB-0A7EA4">
  <img alt="Platform: Windows" src="https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white">
</p>

> 一个基于网易云音乐的 Windows 桌面「息屏歌词」工具：点击按钮后屏幕变为纯黑全屏，以大号字体、按你设置的样式滚动显示当前播放的歌词，模拟手机息屏显示（Always-On Display）的观感。
>
> 文档版本：2026-10-18 ｜ 适用程序版本：当前主分支

---

## 语言构成

| 语言 | 占比 | 构成 |
| --- | --- | --- |
| 🟦 **Python** | **58.1%** | `████████████████████████` |
| 🟧 **HTML** | **33.5%** | `██████████████` |
| 🟪 **CSS** | **7.8%** | `███` |
| 🟨 **Batch** | **0.7%** | `▏` |

> 统计口径：项目自有源码的非空行数（共 1841 行，不含依赖、文档与 skill 文件）。
> 由 **DeepSeek V4.1 Flash** 完成 ｜ 作者：**XYX0809**（第一贡献者）、**BA4IHB** ｜ 开源许可证：**MIT**

---

## 目录

1. [项目简介](#1-项目简介)
2. [功能特性](#2-功能特性)
3. [环境要求与安装](#3-环境要求与安装)
4. [快速开始](#4-快速开始)
5. [设置项详解](#5-设置项详解)
6. [工作原理](#6-工作原理)
7. [目录结构](#7-目录结构)
8. [配置与数据文件](#8-配置与数据文件)
9. [常见问题](#9-常见问题)
10. [技术细节与已知限制](#10-技术细节与已知限制)
11. [开发说明](#11-开发说明)
12. [更新记录](#12-更新记录)
13. [免责声明](#13-免责声明)
14. [开源许可证](#14-开源许可证)
15. [贡献者与致谢](#15-贡献者与致谢)

---

## 1. 项目简介

「163 Music AOD（网易云音乐熄屏歌词）」读取你正在用网易云音乐播放的歌曲，抓取对应歌词，并以**全屏纯黑 + 大字歌词**的方式展示在屏幕上，适合作为桌面摆件、副屏歌词、听歌时的沉浸式展示。

它不修改网易云客户端、不注入内存、不读取账号密码，只使用：

- **网易云主窗口标题**读取当前歌曲；
- **网易云调试端口（CDP）**读取真实播放进度与歌曲 ID（可选，用于精确同步）；
- **网易云公开接口**下载歌词（含翻译数据，界面当前不展示翻译）。

---

## 2. 功能特性

### 2.1 显示规则

- 无论中文还是英文歌曲，页面统一显示 **5 句歌词**；
- 第 **3 句**为当前句（居中）；
- 当前句字号 **100%**，并带光晕与流光效果；
- 相邻句 **82%**、再次 **72%**、更远的句子 **62%**；
- 非当前句做**上下渐变模糊**（越远越模糊、越透明）；
- 句子两端做**侧边渐变淡出**（可调强度）；
- 英文歌**不显示中文翻译**（界面统一为 5 句原文）；
- 当前句靠近歌曲开头/结尾时，5 句窗口自动贴边，不会留空。

### 2.2 视觉与动效

| 效果 | 说明 |
| --- | --- |
| 光晕 | 当前句文字外发光，颜色可调 |
| 流光扫字 | 当前句表面有流动光带扫过 |
| 呼吸动画 | 当前句轻微缩放与明暗呼吸 |
| 渐变模糊 | 非当前句按距离模糊、透明 |
| 侧边模糊 | 歌词左右两端渐变淡出 |
| 逐字显现 | 超长句（仍超出屏幕时）从左到右逐字出现 |
| 平滑滚动 | 歌词切换使用 ease-out 缓动，跟手不拖沓 |

### 2.3 同步能力

- **精确同步**（需网易云以调试模式启动）：暂停、拖动进度条、切歌、倍速播放均准确跟随；
- **近似同步**（未开调试端口）：本地计时器估算，连续播放仍可用，暂停/拖动会暂时错位；
- 设置窗口底部有**同步状态指示灯**：绿色 = 精确同步，橙色 = 近似同步；
- 一键「以调试模式重启网易云」按钮，自动带 `--remote-debugging-port=9223` 启动客户端。

### 2.4 操作方式

| 操作 | 说明 |
| --- | --- |
| 点击「开启息屏歌词」 | 进入全屏黑色歌词界面 |
| `ESC` | 退出歌词界面，回到设置窗口 |
| `Ctrl + Alt + Q` | 全局热键，任何时刻退出歌词界面 |
| `Alt + F4` | 关闭歌词窗口 |
| 设置窗口关闭 | 退出程序 |

---

## 3. 环境要求与安装

### 3.1 系统要求

- Windows 10 / 11（本项目在 Windows 11 Pro for Workstations 上验证）；
- Microsoft Edge **WebView2 Runtime**（Windows 11 通常已内置；缺失时程序会弹窗提示）；
- Python **3.10+**（安装时勾选「Add Python to PATH」）；
- 网易云音乐桌面客户端（3.x 版本已验证）。

### 3.2 依赖

项目依赖已在 `requirements.txt` 中声明：

```
pywebview>=6.0        # WebView2 窗口宿主
requests>=2.28        # 网易云公开接口
pywin32>=305          # Win32 窗口/热键/字体枚举
websocket-client>=1.5 # CDP 调试端口通信
```

### 3.3 安装

双击 **`run.bat`** 即可。首次运行会自动：

1. 在项目目录创建 `.venv` 虚拟环境；
2. 安装 `requirements.txt` 中的依赖；
3. 启动程序。

也可手动安装：

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

---

## 4. 快速开始

1. 打开网易云音乐并**播放任意歌曲**；
2. 双击 `run.bat`，出现设置窗口；
3. （推荐）确认底部指示灯为绿色。若为橙色，点击「以调试模式重启网易云」，稍候重新播放；
4. 调整字体、字号、颜色、间距等效果，顶部预览即所见；
5. 点击 **「开启息屏歌词」**，屏幕进入全屏黑色歌词；
6. 按 `ESC`（或 `Ctrl+Alt+Q`）退出。

设置会自动保存到 `settings.json`，下次启动沿用。

---

## 5. 设置项详解

| 设置项 | 范围 / 默认 | 说明 |
| --- | --- | --- |
| 字体 | 系统字体，默认「微软雅黑」 | 自动枚举系统中已安装的 300+ 字体，中文常用字体优先；也可手动输入字体名 |
| 字号 | 16–200 px，默认 **110** | 当前句的字号；相邻句按比例缩小 |
| 透明度 | 20–100%，默认 100% | 歌词整体透明度 |
| 垂直位置 | 0–100%，默认 50% | 歌词在屏幕中的垂直位置（0 顶部、50 居中、100 底部） |
| 文字颜色 | 默认 `#ffffff` | 歌词文字颜色 |
| 光晕颜色 | 默认 `#4da6ff` | 当前句文字外发光的颜色 |
| 侧边模糊 | 0–100，默认 30 | 歌词左右两侧渐变淡出强度 |
| 呼吸动画 | 开 / 关，默认开 | 当前句轻微缩放 + 明暗呼吸 |
| 流光扫字 | 开 / 关，默认开 | 当前句表面的流动光带 |

顶部黑色预览区域按**全屏比例压缩**显示，字号层级、行距、光晕与全屏一致，调试时可直观对比。

---

## 6. 工作原理

### 6.1 总体架构

```
┌─────────────────────┐        ┌──────────────────────────┐
│  网易云音乐客户端     │        │       本程序              │
│  3.x (CEF)          │        │                          │
│                     │ 标题    │  NetEaseWindowReader     │
│  主窗口标题          ├───────►│  （0.2s 轮询「歌名-歌手」）│
│  "歌名 - 歌手"       │        │                          │
│                     │ CDP    │  NetEaseCdpReader        │
│  调试端口 9223       ├───────►│  （0.1s 读取进度+歌曲ID）  │
│  range input 进度    │        │                          │
└─────────────────────┘        │          │               │
                               │          ▼               │
┌─────────────────────┐        │     LyricProvider        │
│ 网易云公开接口        │◄───────┤  （搜索/歌词/缓存/重试）   │
│  search / lyric      │        └──────────┬───────────────┘
└─────────────────────┘                   │ get_state()
                                          ▼
                               ┌──────────────────────────┐
                               │  pywebview 覆盖层窗口      │
                               │  ui/overlay.html         │
                               │  5 句歌词 + 动效 + 全屏   │
                               └──────────────────────────┘
```

程序由两个 WebView2 窗口组成：

- **设置窗口**（`ui/settings.html`）：参数调节与实时预览；
- **覆盖层窗口**（`ui/overlay.html`）：平时以 1×1 像素在后台预加载（用户不可见），点击开启时用 Win32 `SetWindowPos` 铺满屏幕。

### 6.2 当前歌曲识别

读取网易云主窗口（窗口类 `OrpheusBrowserHost`）的标题，格式为 **「歌名 - 歌手」**。暂停时标题仍保留，因此暂停也能显示歌词。

作为回退，会枚举 `cloudmusic.exe` 进程的顶层窗口标题。

### 6.3 歌曲 ID 与播放进度（CDP）

当网易云以调试端口启动时，程序通过 CDP（Chrome DevTools Protocol）在页面中执行 JS：

- **当前歌曲 ID**：读取播放栏 `#page_pc_mini_bar` 的 `data-log` 中的 `s_cid`；
- **播放进度**：读取进度条内部隐藏的 `input[type=range]` 的 `value` / `max`（毫秒级精度，但界面约每 0.94 秒刷新一次）。

为了获得平滑的歌词切换，程序做了**采样 + 本地插值**：

- 每次采样更新时校正位置；
- 两次采样之间按估计的播放速率本地推算（支持倍速）；
- 约 1.4 秒进度无增长判定为暂停，位置冻结。

未连接调试端口时，回退为「切歌归零的本地计时器」，连续播放仍准确。

### 6.4 歌词获取

优先级：

1. **按歌曲 ID 直连**（有 CDP 时）：`/api/song/lyric?id=...`，一次请求即可，约 100–300ms，且版本 100% 对应；
2. **搜索匹配**（无 CDP 或用歌名时）：`/api/search/get` 搜索 → 按标题/歌手/翻唱标记评分选出最佳结果 → 下载歌词。

其他机制：

- **内存缓存**：同一首歌再次播放时秒切；
- **自动重试**：临时网络失败每 2 秒重试，最多 3 次；确认无歌词（纯音乐）则不再重试；
- **限流**：搜索请求间隔 ≥ 0.6 秒，避免网易云接口返回 405；
- **多端点回退**：优先稳定的旧接口，失败时切换新接口。

歌词经 LRC 解析、元信息行过滤、时间轴排序后交给前端。

### 6.5 排版与渲染

- 前端每 100ms 从 Python 拉取一次状态（`pywebview.api.get_state()`）；
- 以当前句为中心维护 **5 句窗口**，靠近开头/结尾自动贴边；
- 每句字号 = 用户字号 × 距离系数（`1.0 / 0.82 / 0.72 / 0.62`）；
- 单句若仍超出屏幕宽度，会在自身范围内等比缩小以保证完整显示；
- 句间空隙 = 0.62 × 该句字号，行高 1.32 × 字号；
- 列表整体通过 `translateY` 定位，当前句居中；大跨度跳变（拖进度/切歌）时跳过动画直接到位。

### 6.6 全屏与焦点

- 屏幕尺寸和窗口位置在 **per-monitor DPI 感知上下文**中获取并设置，避免 150% 缩放下窗口只铺满 2/3 屏幕；
- 覆盖层为无边框、置顶窗口，覆盖任务栏；启动时去除 Win11 的圆角与边框；
- 窗口使用 `WS_EX_TOOLWINDOW` 从任务栏/Alt+Tab 隐藏；
- 页面 `cursor: none` 隐藏鼠标指针；
- 开启后强制将覆盖层带到前台，保证 `ESC` 生效；
- 退出时覆盖层缩回 1×1 并继续后台渲染，同时把设置窗口带回前台。

### 6.7 动效设计原则

界面动效遵循 `emil-design-eng` skill 中的设计工程原则（已安装于 `.claude/skills/emil-design-eng/`）：

- 统一使用**强 ease-out 曲线** `cubic-bezier(0.23, 1, 0.32, 1)`，避免 `ease-in` 带来的迟滞感；
- 歌词行透明度/模糊过渡 250ms，列表滚动 320ms；
- 用模糊桥接行与行之间的切换，避免「两个对象硬切」的割裂感；
- 连续重复歌词不重播逐字动画，避免闪烁。

---

## 7. 目录结构

```
网易云/
├── app.py                  # 主程序：设置窗口 + 覆盖层窗口 + JS 桥接 + 全局热键
├── netease.py              # 数据层：窗口标题/CDP 读取、歌词获取、LRC 解析、排版数据
├── ui/
│   ├── settings.html       # 设置面板（字体、字号、颜色、预览、开启按钮）
│   ├── overlay.html        # 全屏歌词覆盖层（5 句窗口、层级字号、动效）
│   └── lyrics.css          # 歌词共享样式（光晕、流光、呼吸、模糊、过渡）
├── settings.json           # 用户设置（自动生成/保存）
├── requirements.txt        # Python 依赖
├── run.bat                 # 一键启动（首次自动安装依赖）
├── README.md               # 简要说明
├── PROJECT.md              # 本文档（完整项目文档）
└── .claude/
    └── skills/
        └── emil-design-eng/SKILL.md   # 已安装的设计/动效指导 skill
```

---

## 8. 配置与数据文件

### `settings.json`

```json
{
  "font_family": "微软雅黑",
  "font_size": 110,
  "opacity": 100,
  "vertical_position": 50,
  "text_color": "#ffffff",
  "glow_color": "#4da6ff",
  "side_blur": 30,
  "breathing": true,
  "sweep": true
}
```

- 点击「开启息屏歌词」时自动保存；
- 删除该文件可恢复默认设置；
- 字号默认 110。

### 调试端口

网易云需以如下方式启动才能获得精确同步：

```
cloudmusic.exe --remote-debugging-port=9223
```

设置窗口的「以调试模式重启网易云」按钮会自动完成关闭 → 带参数启动。

---

## 9. 常见问题

### Q1：提示缺少 WebView2

安装 [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)。Windows 11 一般已内置。

### Q2：一直显示「未检测到播放中的音乐」

- 确认网易云**正在播放**（而非仅打开）；
- 程序读取的是主窗口标题，若客户端窗口标题不含「歌名 - 歌手」，请恢复主界面（不要进入某些特殊模式）。

### Q3：同步状态灯是橙色（近似同步）

网易云未以调试端口启动。点击设置窗口底部「以调试模式重启网易云」，重启后重新播放即可变为绿色。

### Q4：歌词与播放进度短暂错位

- 绿色状态（精确同步）下一般不会错位；
- 橙色状态（近似同步）下，暂停/拖动进度条会造成暂时错位，切到下一首或从歌曲开头播放即可恢复。

### Q5：歌词匹配到了翻唱版本

有 CDP 时按歌曲 ID 直连，不会匹配错误；无 CDP 时按「歌名 + 歌手」评分匹配，个别翻唱/同名歌曲可能匹配到其它版本，但歌词内容通常一致。

### Q6：某首歌显示「未找到歌词」

- 纯音乐/无歌词歌曲会在一两次请求后明确提示；
- 网络偶发失败会自动重试 3 次；
- 若持续失败，可切歌后再切回触发重新获取。

### Q7：开启后不是全屏 / 有边框

- 程序已针对 150% DPI 缩放做了 per-monitor 适配，正常应铺满整屏（含任务栏区域）；
- 若仍异常，请确认没有其他置顶工具强制改变了窗口位置，并可尝试重启程序。

### Q8：按 ESC 没反应

- 确认覆盖层处于前台（开启时会自动置顶并激活）；
- 任何情况下都可用全局热键 `Ctrl + Alt + Q` 退出。

### Q9：启动时闪过黑屏

当前版本覆盖层以 1×1 后台预加载，正常不会闪现；若出现，请确认使用的是最新代码并重启。

---

## 10. 技术细节与已知限制

### 10.1 进度精度

- CDP 读取的进度为毫秒级数值，但网易云界面约每 0.94 秒才刷新一次；
- 程序用本地插值补平，切换误差通常在 100–300ms 内；
- 暂停判定有约 1.4 秒延迟（用于区分「界面未刷新」与「真正暂停」）。

### 10.2 调试端口的依赖

- 未开启调试端口时，无法读取真实进度与歌曲 ID；
- 部分网易云版本或安全软件可能限制调试端口；
- 调试端口仅绑定本机 `127.0.0.1`，不会暴露到局域网。

### 10.3 歌词来源

- 使用网易云公开接口，歌词版权归原作者/平台所有；
- 界面当前不展示翻译，但数据层保留翻译字段，后续可扩展。

### 10.4 多显示器

- 覆盖层铺满**主显示器**；多屏环境下其他屏幕不受影响。

### 10.5 字体

- 字体列表来自系统已安装字体，约 300+ 个；
- 不存在的字体名会自动回退到系统默认字体。

---

## 11. 开发说明

### 11.1 关键模块

| 文件 | 职责 |
| --- | --- |
| `app.py` | 窗口创建、DPI/全屏摆放、全局热键、JS ↔ Python 桥接、字体枚举、调试端口重启 |
| `netease.py` | 标题/ CDP 读取、LRC 解析、搜索匹配、歌词下载、缓存/重试、进度插值 |
| `ui/overlay.html` | 状态轮询、5 句窗口、层级字号、逐字显现、滚动定位 |
| `ui/settings.html` | 设置读取/保存、实时预览、字体列表加载、同步状态 |
| `ui/lyrics.css` | 歌词视觉样式与动效 |

### 11.2 主要 API（JS 侧）

`pywebview.api` 暴露：

- `get_settings()`：读取设置；
- `get_state()`：获取播放状态与歌词（每 100ms 轮询）；
- `start_overlay(settings)`：保存设置并全屏开启；
- `close_overlay()`：退出全屏并回到设置窗口；
- `get_sync_status()`：返回是否已连接 CDP；
- `restart_netease_debug()`：以调试端口重启网易云；
- `get_fonts()`：枚举系统字体；
- `quit_app()`：退出程序。

### 11.3 本地调试

- 可用环境变量 `AOD_AUTO_OPEN=1` 让程序启动后自动开启覆盖层，便于截图/联调；
- 语法检查：

```bash
.venv\Scripts\python.exe -m py_compile app.py netease.py
```

- 重新安装依赖：

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 12. 更新记录

| 版本/日期 | 主要变更 |
| --- | --- |
| 2026-10-18 | 统一显示 5 句（中英文一致、去掉翻译）；当前句突出、相邻句递进缩小；句间间距加大；应用 emil-design-eng 动效规范 |
| 2026-10-18 | 多字体支持（枚举系统 300+ 字体）；默认字号 110；修复布局视口高度问题 |
| 2026-10-17 | 距离层级字号；翻译字号固定比例；修复连续重复歌词闪烁 |
| 2026-10-17 | 修复 DPI 缩放导致的非全屏；翻译带光晕；ESC 退出回到设置 |
| 2026-10-17 | 直连歌曲 ID 取歌词（约 300ms）；自动重试；进度插值；确认全屏与焦点 |
| 2026-10-17 | 初版：设置窗口 + 全屏歌词覆盖层 + 光晕/流光/呼吸/模糊 |

---

## 13. 免责声明

本项目为个人学习与自用工具，与网易云音乐及网易公司无任何隶属关系。歌词数据来自公开接口，版权归原权利人所有，请勿用于商业用途。使用调试端口仅限本机，请勿向公网开放。

---

## 14. 开源许可证

本项目采用 **MIT License** 开源。

```
MIT License

Copyright (c) 2026 XYX0809, BA4IHB

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 15. 贡献者与致谢

**贡献者**

| 贡献者 | 角色 |
| --- | --- |
| **XYX0809** | 第一贡献者 · 项目发起与主要开发 |
| **BA4IHB** | 贡献者 · 方案讨论与功能验证 |

> 本项目贡献者仅上述两位。

**制作工具**

- [DeepSeek V4.1 Flash](https://www.deepseek.com/)

**致谢**

- 界面与动效设计参考 [emilkowalski/skills](https://github.com/emilkowalski/skills)（Emil Kowalski）的设计工程原则；
- 感谢网易云音乐提供的公开歌词接口。

---

<p align="center">
  <sub>Made with ❤️ by XYX0809 &amp; BA4IHB · Powered by DeepSeek V4.1 Flash · MIT License</sub>
</p>
