# 163 Music AOD · 网易云音乐熄屏歌词

<p>
  <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg">
  <img alt="Python" src="https://img.shields.io/badge/Python-60%25-3572A5?logo=python&logoColor=white">
  <img alt="HTML" src="https://img.shields.io/badge/HTML-33.3%25-E34C26?logo=html5&logoColor=white">
  <img alt="CSS" src="https://img.shields.io/badge/CSS-6.1%25-563D7C?logo=css3&logoColor=white">
  <img alt="Batch" src="https://img.shields.io/badge/Batch-0.6%25-C1F12E">
</p>
<p>
  <img alt="Made with DeepSeek V4.1 Flash + Claude Code" src="https://img.shields.io/badge/Made%20with-DeepSeek%20V4.1%20Flash%20%2B%20Claude%20Code-6F42C1">
  <img alt="Made with MiMo v2.5 Pro" src="https://img.shields.io/badge/Made%20with-MiMo%20v2.5%20Pro-FF6900">
  <img alt="Authors: XYX0809 & BA4IHB" src="https://img.shields.io/badge/Authors-XYX0809%20%26%20BA4IHB-0A7EA4">
</p>

一个基于 **网易云音乐** 的「息屏歌词」桌面小工具：点击按钮后屏幕变为纯黑背景，按你的设置以大字显示当前播放的歌词，模拟手机息屏显示歌词的效果。

- 无论中文还是非中文歌词，都显示 **5 句**，第 3 行为当前歌词；
- 当前句字号最大并带光晕，相邻句依次缩小（82% / 72%），更远的行上下渐变模糊；
- 不显示翻译（中英文歌一致）。

## 功能

| 设置项 | 说明 |
| --- | --- |
| 字体 | 歌词字体（可输入任意已安装字体名） |
| 字号 | 歌词字号（16–120px） |
| 透明度 | 歌词整体透明度 |
| 垂直位置 | 歌词在屏幕上的上下位置（0=顶部，50=居中，100=底部） |
| 文字颜色 | 歌词文字颜色 |
| 光晕颜色 | 文字发光颜色 |
| 侧边模糊 | 歌词左右两侧的渐变淡出/模糊程度 |
| 呼吸动画 | 当前行轻微缩放 + 明暗变化 |
| 流光扫字 | 当前行表面流动的光带效果 |

## 使用

1. 安装 Python 3.10+（需勾选「Add Python to PATH」）。
2. 双击 `run.bat`（首次会自动创建虚拟环境并安装依赖）。
3. 打开网易云音乐并**播放**任意歌曲。
   - 想要**精确同步**（暂停/拖进度/切歌都不偏移）：在设置窗口点一次「以调试模式重启网易云」，再重新播放。
   - 否则为近似同步（连续播放仍准确，暂停/拖进度会暂时错位）。
4. 在设置窗口调整好效果，点击底部「**开启息屏歌词**」。
5. 屏幕变黑并显示歌词。退出方式：
   - 按 **ESC** 键；
   - 或按全局热键 **Ctrl + Alt + Q**；
   - 或按 **Alt + F4**。

设置会自动保存到 `settings.json`，下次启动沿用。

## 原理

- **当前播放信息**：读取网易云主窗口标题（格式为「歌名 - 歌手」），无需修改客户端。
- **歌词来源**：网易云音乐公开接口（搜索 + 歌词下载，含翻译），LRC 时间轴与播放进度对齐。
- **进度对时**：优先通过网易云调试端口（CDP，端口 9223）读取真实播放进度——暂停、拖进度条、切歌都精确同步；若网易云未以调试模式启动，则回退为本地计时器估算（连续播放仍准确，暂停/拖进度会暂时错位）。

> 未检测到播放中的音乐时，黑屏会提示「请先在网易云音乐中播放歌曲」。请确保网易云正在播放（而非仅打开、且主窗口标题能显示歌名）。

## 目录结构

```
├── app.py             # 主程序（设置窗口 + 覆盖层窗口）
├── netease.py         # 数据层（窗口标题读取 + 歌词抓取 + LRC 解析）
├── ui/
│   ├── settings.html  # 设置面板
│   ├── overlay.html   # 全屏歌词覆盖层
│   └── lyrics.css     # 歌词样式（光晕/流光/呼吸/模糊）
├── requirements.txt
└── run.bat
```

## 常见问题

- **提示缺少 WebView2**：安装 [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)（Windows 11 通常已内置）。
- **一直显示「未检测到播放中的音乐」**：请确认网易云正在播放；程序读取的是网易云主窗口标题，若网易云最小化到托盘后窗口标题不含歌名，则读不到。
- **歌词对不上时间**：未以调试模式启动网易云时会用近似同步，暂停/拖进度会导致错位。点设置窗口里的「以调试模式重启网易云」后重新播放即可精确同步。
- **歌词不匹配**：搜索采用「歌名+歌手」匹配，个别翻唱/同名歌曲可能匹配到其它版本（歌词通常一致），属正常现象。
- **启动失败**：查看目录下的 `startup_error.log`。

## 免责声明

本项目为个人学习用途的独立工具，与网易云音乐及网易公司无关；歌词数据来自公开接口，请勿用于商业用途。

## 许可证与作者

- 开源许可证：**MIT**（详见 [LICENSE](LICENSE)）
- 作者：**XYX0809**、**BA4IHB**
- 完整项目文档：[PROJECT.md](PROJECT.md)

## Contributors

- [XYX0809](https://github.com/XYX0809) — 项目发起与主要开发
- [BA4IHB](https://github.com/ba4ihb) — 方案讨论与功能验证

---

## 制作工具

本项目在开发过程中使用了以下 AI 工具辅助（工具不计入贡献者）：

- DeepSeek V4.1 Flash
- Claude Code
- MiMo v2.5 Pro
