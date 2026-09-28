# kerneltop

`kerneltop` 是一个把内核函数命中次数（profiling histogram）按 `top` 那种整屏刷新的
方式显示出来的命令行工具。它读取 `/proc/profile` 里的采样计数，再用 `System.map`
把地址还原成函数名，按 tick 数从高到低打印最热的内核函数。作者 Randy Dunlap，
源码自述 "shows kernel function usage in a style like 'top'，derived from
readprofile.c"，许可证 GPL-2.0-or-later。

## 功能概述

- 读取 `/proc/profile` 的原始采样桶（第一个 `u32` 是 `sampling_step`，其后是每个
  桶的 tick 计数），每轮读取后与上一轮做差分，因此显示的是"这段时间内"的热度。
- 从 `System.map` 里取 `_stext` 与 `_etext` 之间的 `T`/`t` 符号建地址索引，
  并校验地址单调不减。
- 支持 `-m MAPFILE`（默认 `/boot/System.map`，会依次再试 `-uname -r` 后缀与
  `/lib/modules/...`）、`-p PROFFILE`（默认 `/proc/profile`）、`-l LINES`、
  `-s SECONDS`、`-t TICKS`（阈值）、`-u`（不排序）、`-V`（打印版本并退出）。
- 界面全部由 `vidsupport.h` 里的 ANSI 转义序列拼装（游点定位、清行、反显），
  写的是 `stdout`，因此**不需要 controlling tty**：重定向到文件照样是合法输出。
- 键盘交互走 `termios` 的 raw 化（`keypressed()`），按 `q` 退出、`h` 看帮助。

## 依赖关系

- **编译依赖：无。** 官方 release tar 包只有 `kerneltop.c`、`makefile`（全小写）、
  `vidsupport.h` 三个文件，只用 libc 与内核 UAPI 头（`linux/kd.h` 在 OHOS native
  sysroot 中存在）。
- **运行依赖：`/proc/profile` 可读（需 `CONFIG_PROFILING` 且 root）+ 一个
  `System.map`。** 这两点决定了它在受限沙箱里的可用面：读 profile 那条路需要特权，
  但 CLI 层、map 解析层、地址→符号映射、差分、排序与打印层都不需要。

## OHOS 适配

- 构建系统是裸 makefile：没有 configure、没有 install 目标、`CC=gcc` 写死在文件里。
  交叉编译靠 `make` 命令行变量覆盖（命令行赋值优先于文件内普通赋值），配方不修改
  任何源码，`patches_applied` 为空。
- makefile 的 else 分支是 `CCFLAGS=-s $(CFLAGS)`，即在**链接期** strip。OHOS 内核
  加载 ELF 时要校验 SDK 在链接期写入的 `.codesign` 段，任何**链后**改写 ELF 的动作
  （`llvm-strip`、`objcopy` 改段）都会让产物变成 `exec` 报 `Operation not permitted`
  （rc=126）。本包因此用命令行 `CCFLAGS=` 把 `-s` 从源头摘掉，产物保持 not stripped，
  整条链路上没有任何环节再碰这枚 ELF。细节与否证过程见版本级 `notes.md`。
- 无外部依赖 ⇒ 无 R36 依赖发布风险；无 `.so` 产物 ⇒ 不涉及 R26 系统同名库污染。
- 已知运行面限制（**不是适配缺陷**）：非 root 且内核未开 `CONFIG_PROFILING` 时读不到
  `/proc/profile`，程序会打印 `enable kernel profiling [profile=N]` 并以 1 退出；
  真正的"top 式持续刷新"体验还需要前台终端。

## 与 Linux 的差异

- 上游没有长选项：`--version` / `--help` 会落进 `getopt` 的 `default:` 分支，打印
  usage 并以退出码 1 结束；版本信息要用短选项 `-V` 取。
- 打包不带 man page 与文档件，`package()` 只装一个可执行文件。

## 参考资料

- 官方发布目录：https://www.infradead.org/~rdunlap/src/
  （同目录另有 `kerneltop-0.91.tar.gz` 以及 0.8 / 0.9 子目录）
- 许可证：GPL-2.0-or-later（源码头部为 FSF GPL-2.0+ 标准表述）
