# xrefresh

`xrefresh` 是 X11 的一个极简命令行工具：它在屏幕上临时映射一个全屏的
override-redirect 窗口再立刻取消映射，借此**迫使 X server 重绘全部窗口**。用途是
"屏幕花了/残留脏块"时一键刷新，不需要重启会话。上游把它称作
"Kitchen sink version, useful for clearing small areas and flashing the screen"。

## 功能概述

- 单文件 C 程序（`xrefresh.c`），autotools 构建，安装一个可执行文件 + 一个 man page。
- 选项：`-display/-d`、`-geometry/-g`、`-black`、`-white`、`-solid <color>`、
  `-root`、`-none`、`-delay <ms>`、`-version`、`-help`；支持唯一前缀缩写（如 `-v`）。
- 默认等价于 `xrefresh -none -delay 0`。
- 位置参数可给 geometry 与 display。
- 它本身不"修复"任何东西：真正干活的是 X server 收到暴露事件后的重绘。

## OHOS 适配

上游没有任何 HarmonyOS 平台代码需要移植——适配量全在**构建探测层**：

| 适配点 | 说明 | 知识条目 |
|---|---|---|
| `config.guess` | 增加 `*:HarmonyOS:*:*` 分支，输出 `aarch64-unknown-linux-ohos`；同时短路掉会在 HMDFS 上写不进 `dummy.c` 的编译器探测 | E007 / E160 |
| `config.sub` | 三处白名单：`ohos-linux` 映射、OS 白名单 `ohos*`、kernel-OS 组合白名单 `linux-ohos*`（缺第三处会报 `Kernel 'linux' not known to work with OS 'ohos'`） | E007 / E072 / E122 |
| `configure` | ① `config.status` 的临时目录引导去掉 `umask 077`（SGID 目录下 HMDFS 会让创建者自己也写不进去）；② 同一枚补丁把 `ac_pwd` 的 `pwd` 探测改成失败时回退环境变量 `PWD` | E136、E386 |
| 依赖定位 | 走 `XREFRESH_CFLAGS`/`XREFRESH_LIBS` 逃逸口，不依赖 CI worker 的 pkg-config | — |
| 不用三元组 | 按 R1/E205 不拿 `--build/--host` 绕过探测（会被误判成交叉编译，`config.h` 生成错） | E205 |

补丁新增行**不含任何平台宏**（R8/PF5）：平台能力由 `config.guess`/`config.sub`
的探测结果决定，而不是在源码里 `#ifdef` 硬编码。

已知限制：`xrefresh` 是真正的 X 客户端，**必须能连上一个运行中的 X server** 才做
实事。无 `DISPLAY` 时它干净报错退出（`unable to open display ''`，rc=1），不会挂住；
不可达的 `DISPLAY=:99` 同样快速失败。因此"重绘窗口"这一实质行为只能在有真 X 会话时
观察，自动化测试覆盖的是版本/参数/退出码与运行期动态链接闭包。

## 依赖关系

- 构建 + 链接：`libx11`（提供 `libX11.so.6` 与 `x11.pc`）、`xorgproto`
  （提供 `X11/Xos.h`、`X11/Xfuncproto.h` 与 `xproto.pc >= 7.0.25`；注意其 `.pc`
  落在 `share/pkgconfig/`）。
- 运行期闭包：`libX11.so.6 → libxcb.so.1 → libXau.so.6 + libXdmcp.so.6`。
- 构建工具：clang/make（上游已预生成 `configure`，不需要 autoconf/automake）。
- **不需要** libXext / libXt / libXmu：`configure.ac` 里唯一的模块检查是
  `PKG_CHECK_MODULES(XREFRESH, [x11 xproto >= 7.0.25])`。

## 参考资料

- 源码仓库：<https://gitlab.freedesktop.org/xorg/app/xrefresh>
- 发布归档：<https://xorg.freedesktop.org/archive/individual/app/xrefresh-1.1.0.tar.gz>
- 许可证：MIT（`COPYING`，Open Group / DEC 传统 X 许可证文本）
- 本版本适配记录：`1.1.0/notes.md`
