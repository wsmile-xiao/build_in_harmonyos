# aylet

`aylet` 是一个命令行 AY 音乐文件播放器，用于播放 Sinclair ZX Spectrum 生态中的 AY 音乐。

## 功能

- 解析并播放 AY 音乐文件。
- 提供终端界面和命令行帮助。
- 通过 stdout 输出 PCM 音频数据，便于交给其他播放器或管道处理。

## HarmonyOS PC 适配

- 使用 OHOS aarch64 Clang 工具链构建。
- 上游 OSS 后端依赖 `sys/soundcard.h`，在 OHOS 上不可用；适配增加了可移植的 stdout PCM 后端。
- 上游 curses UI 依赖 OHOS SDK 中不存在的 ncurses 开发头/库；stdout 模式使用等价的无 UI 后端，保留 AY 播放循环和状态输出。
- `ui.c` 的旧代码缺少 `stdlib.h` 声明，配方通过编译选项补充该头文件。
- 当前适配验证的是命令行工具和 stdout PCM 后端的编译/运行入口，不提供 OHOS 原生音频设备播放后端。

## 依赖

- OHOS PC aarch64 SDK/Clang。
- 无额外 Conan 依赖；stdout 模式不链接 ncurses。

## 参考资料

- 源码归档：[aylet 0.5 Debian source archive](https://deb.debian.org/debian/pool/main/a/aylet/aylet_0.5.orig.tar.gz)
- 项目主页：[World of Spectrum](https://www.worldofspectrum.org/)
