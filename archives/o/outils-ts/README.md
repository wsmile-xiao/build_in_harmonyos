# outils-ts

`outils-ts` 提供 `ts(1)` —— “timestamp input”：把标准输入的每一行前置一个时间戳后写到标准输出。它取自 **outils** 工程（作者 Leah Neukirchen），一个把 OpenBSD 的非标准命令行工具移植到 Linux 的合集：<https://github.com/leahneukirchen/outils>。本包是该合集中 `ts` 组件的独立打包（上游同版本 `outils/0.14` 亦含 `ts`）。

## 功能概述

- 默认把每行输入前缀 `%b %d %H:%M:%S` 形式的时间戳；`ts` 只读 stdin、只写 stdout，适合插在管道里给日志加时间
- `-i`：显示与上一行之间的间隔（默认格式 `%H:%M:%S`）
- `-s`：显示自程序启动起经过的时间（默认格式 `%H:%M:%S`）
- `-m`：使用严格线性递增的单调时钟生成时间戳（不受系统时间跳变影响）
- 可选位置参数 `format`：任意 `strftime(3)` 转换说明；并扩展支持 `%.S` / `%.s` / `%.T` 追加微秒（如 `10.00001`、`1656427781.00001`、`4:20:00.00001`）
- `-i` 与 `-s` 互斥；多于一个操作数为用法错误（exit 1，stderr 打印 `usage:`）

上游手册示例：

```sh
$ (echo foo; sleep 2; echo bar) | ts
Jun 28 12:13:38 foo
Jun 28 12:13:40 bar

$ ls | ts -i %.S
00.000452 CVS
00.000595 Makefile
00.000004 ts.1
00.000004 ts.c
```

## 依赖关系

- 编译依赖：无。仅 libc + 同源 `src/liboutils/` 对象（`strlcpy`、`reallocarray` 兼容实现、`pledge` 空实现）
- 运行依赖：无。产物为 PIE ELF64，唯一 `NEEDED` 为 `libc.so`

## OHOS 适配

- **补丁 0001（唯一改动）**：OHOS 的 musl libc 不提供 `reallocarray(3)`（glibc 提供），而上游 Makefile 的 ts 链接闭包只含 `ts.o + liboutils/strlcpy.o + liboutils/pledge.o`，链接期报 `undefined symbol: reallocarray`。补丁把同源兼容对象 `src/liboutils/reallocarray.o` 加入 ts 目标（与同源 `rs`/`rdate` 目标写法一致）。未改动任何 `.c/.h`，无平台宏注入
- **零第三方依赖**：`requires` = 0；`pledge(3)` 在 Linux/OHOS 下即同源空实现
- **打包**：上游 `make install` 依赖 coreutils `install(1)` 且写入写死的系统 `PREFIX`，配方 `package()` 改为用 Conan `copy()` 直接落 `bin/ts`、`share/man/man1/ts.1`、`licenses/LICENSE`
- **测试补全**：上游无自动化测试（13 个 Makefile 无 `test/check/regress` 目标、无 `tests/` 目录、无 CI 配置），`test_package` 按 ts(1) 手册补全 10 组 23 断言，其中 11 项为鸿蒙特有（reallocarray 扩容路径 + 打包 ELF 的 AArch64/PIE/musl/依赖形状）

## 参考资料

- 上游仓库：<https://github.com/leahneukirchen/outils>
- 手册：包内 `share/man/man1/ts.1`；`ts` 无 `--help`/`--version`
- 同源父工程包：`outils/0.14`（含 apply/calendar/cksum/jot/lam/lndir/md5/rdate/rs/signify/ts/unvis/vis/what）

## 版本

- `0.14` — 适配 HarmonyOS PC（aarch64-linux-ohos / armv8），1 个可移植性补丁（补链 reallocarray 对象）、零第三方依赖；test_package 23/23 通过；详见 [0.14/notes.md](0.14/notes.md)

## 产物

- `bin/ts`
- `share/man/man1/ts.1`
- `licenses/LICENSE`
