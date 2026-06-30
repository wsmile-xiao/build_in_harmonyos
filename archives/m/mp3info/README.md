# mp3info

MP3 technical info viewer and ID3 1.x tag editor.

mp3info 是一个用于查看 MP3 文件技术信息（比特率、采样率、播放时长等）和编辑 ID3 1.x 标签（标题、艺术家、专辑等）的命令行工具。

它还提供一个基于 ncurses 的交互式界面，方便用户浏览和编辑 MP3 文件的标签信息。

## 主要功能

- 显示 MP3 文件的技术属性：MPEG 版本、层、比特率、采样率、播放时长
- 编辑 ID3 1.x 标签：标题、艺术家、专辑、年份、注释、曲目编号、流派
- 交互式 ncurses 界面
- 格式化输出（自定义 printf 风格的格式字符串）
- 查看和删除 ID3 标签

## 编译说明

- 构建系统：纯 Makefile（非 autotools）
- 依赖：ncurses（静态库）+ libtinfow（动态库）
- gmp3info（GTK2 GUI 版本）因系统无 GTK2 未编译
- mp3info 不支持 `--version` 参数，版本信息通过 `-h` 获取

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.8.5a | published | 2026-06-12 |
