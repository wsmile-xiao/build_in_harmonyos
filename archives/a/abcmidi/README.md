# abcmidi

abcMIDI 是一套用于处理 ABC 记谱法（abc notation）的命令行工具集。ABC 是一种用纯文本格式记录音乐的计算机语言，由 Chris Walshaw 在 1993 年引入。

abcMIDI 包由 James Allwright 在 1990 年代用 C 语言编写，后由 Seymour Shlien 接手维护至今。

## 核心程序

| 程序 | 功能 |
|------|------|
| **abc2midi** | 将 ABC 记谱文件转换为 MIDI 音乐文件 |
| **midi2abc** | 将 MIDI 文件逆向转换为 ABC 记谱格式 |
| **abc2abc** | ABC 格式转换和重组 |
| **midicopy** | MIDI 文件复制、通道/时间区间提取 |
| **mftext** | 将 MIDI 文件解析为文本格式输出 |
| **midistats** | 统计 MIDI 文件的音符、通道、节奏等数据 |
| **abcmatch** | ABC 文件模式匹配搜索 |
| **yaps** | 将 ABC 文件渲染为 PostScript 乐谱 |

## 官方资源

- 官方网站: https://ifdo.ca/~seymour/runabc/top.html
- 源码仓库: https://github.com/sshlien/abcmidi
- Savannah 下载: https://download.savannah.nongnu.org/releases/abcmidi/
- SourceForge 下载: https://sourceforge.net/projects/abcmidi/

## 构建系统

autotools (configure + make)

## 依赖

仅依赖 libm（数学库，系统自带），无其他外部库依赖。

## 编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 2026.02.24 | published | 2026-06-03 |