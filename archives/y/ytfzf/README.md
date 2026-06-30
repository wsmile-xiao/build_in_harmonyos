# ytfzf

ytfzf 是一个 POSIX shell 脚本工具，用于在终端搜索和观看 YouTube 视频（无需 API 密钥）。

## 功能概述

- 搜索 YouTube 视频、频道、播放列表
- 支持 Invidious 实例作为搜索源
- 支持多种缩略图查看器（ueberzug、sixel、kitty 等）
- 支持订阅管理
- 支持多种 URL 处理器（mpv、vlc 等）
- 支持多种扩展插件

## OHOS 适配

- **构建系统**: makefile（纯 shell 脚本，无 C 编译）
- **安装方式**: `make install doc addons PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX`
- **TMPDIR**: 使用 `${TMPDIR:-/tmp}`，正确适配 HarmonyOS（无需 E002 补丁）
- **YTFZF_SYSTEM_ADDON_DIR**: Makefile 的 install 步骤自动用 sed 替换路径，确保非 /usr/local 前缀下 addons 路径正确
- **无 ELF 二进制**: ytfzf 是 shell 脚本，ELF 签名/strip/RPATH 不适用

## 运行依赖

- **jq**（JSON 解析器，ytfzf 运行必须依赖）
- **curl**（HTTP 请求，系统自带）
- **fzf**（交互式选择界面）
- **mpv** 或其他视频播放器（可选）

## 参考资料

- 源码仓库: https://github.com/pystardust/ytfzf
- 版本: v2.6.2 (FINAL)