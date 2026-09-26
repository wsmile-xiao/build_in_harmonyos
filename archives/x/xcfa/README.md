# XCFA (X Convert File Audio)

XCFA 是一套基于 GTK3 的音频文件处理工具，用于从 CD 抓轨、在不同音频格式之间
转换、规范化音量、按 cue 分割、批量重命名与读写标签；随包提供图形界面
（`bin/xcfa`）与命令行工具（`bin/xcfa_cli`）。

## 功能概述

- 音频转换：wav / flac / ape / wavpack / ogg / m4a / mpc / mp3 / wma / shorten /
  rm / dts / aif / ac3 → wav / flac / ape / wavpack / ogg / m4a / mpc / mp3 / aac
- ReplayGain 音量分析（flac / mp3 / ogg / wavpack）与 wav 归一化
- CD 抓轨（cdparanoia/icedax）、cue 文件解析与整轨分割
- wav 采样率 / 声道 / 位深重采样，标签读写（taglib），外部程序集成与状态栏日志
- `xcfa_cli` 提供同一能力的命令行入口（`--info_files` / `--info_tags` / `--info_head`
  可直接分析文件）

## OHOS 适配（HarmonyOS PC / OpenHarmony aarch64）

- 构建系统：autotools（上游 tarball 自带 `configure`）；平台识别由构建期替换的
  OHOS-aware `config.guess`/`config.sub` 完成（E007）。
- 编译期约束：`configure.ac` 会整体重写 CFLAGS，因此 `-fcommon`、依赖 `-I`、
  构建路径脱敏的 prefix-map 全部经 `CPPFLAGS` 注入；`LIBS` 负责静态
  `libtag.a`/zlib/libc++ 与 glib 代理 libintl 的链接。
- 依赖（Conan 制品仓）：`gtk/3.24.43`、`vte/0.74.2`、`taglib/1.13.1`
  （1.x 才带 C 绑定 `libtag_c`）、`alsa-lib/1.2.16`、`curl/8.15.0`、
  `libx11/1.8.13` + `xorgproto/2025.1`、`zlib/1.3.1.1`。
- 补丁（9 个，均为通用可移植性修复）：移除 5 处未使用的 `<cairo-xlib.h>`
  （OHOS cairo 未启用 xlib 后端）；`win_vte.c` 增加 `HAVE_VTE` 头文件回退分支；
  `get_current_dir_name()` 改为 `getcwd(NULL, 0)`；`get_info.h`/`tags.h` 显式
  包含 `<sys/types.h>`（`uint`）。
- 运行期：UI 资源（`share/xcfa/glade/*.glade`）按上游 XDG 逻辑经
  `XDG_DATA_DIRS=<prefix>/share` 定位；GUI 需要显示服务，无显示时打印
  `cannot open display` 并以 rc=1 优雅退出。
- NLS（gettext 翻译）保持上游默认探测结果：OHOS 无 gettext 工具链 → `USE_NLS=no`，
  不安装 `po/` 翻译，程序功能不受影响。

## 依赖关系

- 编译依赖：见上（Conan）；另需外部程序提供实际编解码能力（flac/lame/oggenc/
  wavpack/mac/mpcenc/faac/aacplusenc/normalize/sox/shntool/mplayer 等，运行期可选）。
- 运行依赖：gtk3 / vte-2.91 / taglib / alsa-lib / libcurl / libX11（Conan 依赖链）。

## 参考资料

- 官网：http://www.xcfa.tuxfamily.org/ （作者已声明停止维护）
- 源码发布目录：https://download.tuxfamily.org/xcfaudio/xcfa_download/src/
- Debian 包页：https://tracker.debian.org/pkg/xcfa
