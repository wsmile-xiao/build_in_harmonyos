# lemonbar

`lemonbar` 是一条基于 xcb 的 X11 状态栏（dock / panel）：它从标准输入读取一种很小的标记语言（`%{F...}` 前景色、`%{B...}` 背景色、`%{A...}` 可点击区域、`%{O...}` 偏移、`%{c}` 居中、`%{r}` 右对齐等），把每一行渲染成一条停靠在屏幕边缘的窗口。因为完全走 xcb、不依赖 GTK/Qt，它常被 dwm/i3/bspwm 一类窗口管理器的用户当作最轻的状态栏后端。

上游 [LemonBoy/bar](https://github.com/LemonBoy/bar)（作者 LemonBoy 等，MIT）。

## 功能概述

- `lemonbar` — 主程序：读 stdin 渲染状态栏；支持 UTF-8 与内嵌字体/颜色/下划线、可点击区域、`-p` 常驻、`-d` 强制 docking、`-n` 设置 WM_NAME、`-o` 选择输出（RandR）、`-u/-B/-F` 设置下划线高度与前后景色
- 输出协议很小，可用任意脚本（shell/awk/C）生成；`%{A:...:}` 输出鼠标事件为 `button <name>` 行
- 多显示器：经 RandR 枚举输出，可选 `-o` 指定某个/多个输出

## 依赖关系

- 编译依赖：`libxcb/1.17.0.1`（核心 `xcb` 组件 + `xcb-randr` / `xcb-xinerama` 扩展组件，均由该 conan 包提供）
- 运行依赖：`libxcb` 的传递共享库 `libXau`、`libXdmcp`（`libxcb.so.1` 的 `DT_NEEDED`）——本包已随二进制一并装入 `bin/`
- 运行依赖：一个可连接的 X server（无 X 时程序在 `xconn()` 处以 `EXIT_FAILURE` 退出）

## OHOS 适配要点

- 上游纯 POSIX Makefile 未经修改即可用 OHOS SDK clang（aarch64-linux-ohos）交叉编译；**零补丁**
- 编译/链接参数经**环境变量** `CFLAGS`/`LDFLAGS` 注入：Makefile 使用 `CFLAGS += ` 追加语义，改用 make 命令行变量赋值会把上游默认的 `-Wall -std=c99 -Os -DVERSION -D_GNU_SOURCE` 一并吞掉
- 归档来自 tag tarball、内部无 `.git`，Makefile 的 `git describe` 条件赋值必然失配，`VERSION` 会静默退回上游硬编码的 `1.4`；配方在构建时以命令行 `VERSION=1.5` 覆盖，使产物自报版本与 tag 一致
- 上游 Makefile 从不定义 `WITH_XINERAMA`（尽管 README 宣称支持 Xinerama，且无条件链接 `-lxcb-xinerama`）：默认 `make` 会把 xinerama 代码路径与 randr<1.5 的回退分支一起编译掉。本包保持与上游默认产物一致的编译面，未额外打开该特性
- 二进制以 `$ORIGIN` rpath 链接，运行期 `.so` 随二进制安装到 `bin/`：OHOS musl 加载器忽略 `LD_LIBRARY_PATH`，且构建机没有系统 `libxcb`
- 上游**没有测试套件**（Makefile 无 `check`/`test` target，tarball 内无任何测试文件，`check.yml` 只是构建流水线）——审计证据见 [1.5/test_package/MANIFEST.yml](1.5/test_package/MANIFEST.yml)；`test_package` 真实执行已安装的二进制并断言其无 X 时的失败路径

## 参考资料

- 上游仓库：<https://github.com/LemonBoy/bar>
- 标记语言与命令行说明：tarball 内 `README.pod`（可 `pod2man` 生成 man 手册；本包未附带手册，因为构建机不保证有 `pod2man`）
- xcb 协议绑定：<https://xcb.freedesktop.org/>

## 版本

- `1.5` — 适配 HarmonyOS PC（aarch64-linux-ohos / armv8），零补丁；见 [1.5/notes.md](1.5/notes.md)

## 产物

| 路径 | 说明 |
|------|------|
| `bin/lemonbar` | 主程序（arm64 ELF） |
| `bin/libxcb.so*`、`bin/libxcb-randr.so*`、`bin/libxcb-xinerama.so*` | 运行期共享库（$ORIGIN rpath） |
| `bin/libXau.so*`、`bin/libXdmcp.so*` | `libxcb.so.1` 的传递运行期依赖 |
