# FINAL CUT

FINAL CUT 是一个 C++ 终端用户界面库，可在文本终端中绘制控件和管理键盘、鼠标及终端状态。

## 功能概述

- 提供对话框、按钮、列表框、文本框等 TUI 控件。
- 封装终端检测、颜色、光标移动、键盘和鼠标输入处理。
- 提供 `FString` 等文本类型及 UTF-8 与宽字符转换接口。

## OHOS 适配

- 使用 Autotools 构建，目标设备为 HarmonyOS PC aarch64。旧版 Autoconf 生成的 `config.guess`/`config.sub` 可能不识别 `linux-ohos`，配方在构建目录中进行幂等适配。
- 终端 capability 所需的 termcap 头文件和符号由 `ncurses` 提供；Conan 配方将其作为传递依赖。
- 这是终端界面库，不是 ArkUI 图形界面。使用方需要连接交互式终端并提供有效的 `TERM`/terminfo 环境。
- 在已测 HarmonyOS 6.0 aarch64 设备上，内核拒绝 `TIOCSTI` 终端输入注入 ioctl（EACCES）。适配测试仅排除依赖该注入能力的用例，其他键盘测试及库的生产代码保持原样。

## 依赖

| 依赖 | 用途 |
|------|------|
| `ncurses` | 提供 termcap 头文件、终端 capability 符号和 terminfo 数据库 |
| Autoconf、Automake、Libtool | 构建期生成和运行 Autotools 构建脚本 |

## 功能验证

在 HarmonyOS aarch64 环境使用仓库 profile 构建并运行 Conan consumer tests：

```bash
conan create archives/f/finalcut/0.9.1 -pr=ci/conan/profiles/ohos-aarch64
```

## 参考

- [上游仓库](https://github.com/gansm/finalcut)
- [上游 README](https://github.com/gansm/finalcut/blob/master/README.md)
