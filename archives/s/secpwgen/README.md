# secpwgen

`secpwgen` 是一个安全口令/通行短语生成器：从 OpenSSL 的密码学安全随机数发生器（`RAND_bytes`）取熵，再经 Blowfish 计数式 SRNG 扩展，按用户指定的模式与长度生成高熵口令，并报告实际熵值（bits）。生成过程中口令与随机状态都放在 `mlock()` 锁定的内存里，退出前清零，同时关闭 core dump 并丢弃多余权限。

上游作者 Željko Vrba，源码托管在 [itoffshore/secpwgen](https://github.com/itoffshore/secpwgen)（Alpine Linux `community/secpwgen` 亦以此为上游），MIT 许可。

## 功能概述

调用形式固定为 `secpwgen <模式> <N>`（argc 必须为 3）：

- `-p N` / `-pe N` — 从 8192 词 Diceware 词表生成 N 词通行短语；`e` 为增强模式，每个词随机位置插入一个符号（熵 = 13.00/词，增强另加 5.17 + log2(词长)）
- `-s N` / `-se N` — 从 2048 词 S/Key 词表生成（熵 = 11.00/词）
- `-A<类> N` — 生成 N 个随机元素，类别可组合：`a` 字母数字、`d` 十进制、`h` 十六进制、`s` 特殊符号、`y` 3-4 字母音节；组合会按上游规则收敛（含 `a` 时剔除 `d`/`h`，含 `h` 时剔除 `d`，`y` 与其他类共存时退化为 `y`+`d`）
- `-r N` — 输出 N 个随机比特的 BASE64 编码（熵 = 字节数 × 8）
- `-k N` — 输出 koremutake 音节编码（1.3 新增，熵 = 字节数 × 7）

成功时输出三行，中间一行形如 `<口令> ;ENTROPY=52.00 bits`。

## 依赖关系

- 编译依赖：`openssl/3.5.6`（`<openssl/rand.h>`、`<openssl/blowfish.h>`、`<openssl/err.h>` + `-lcrypto`）；另需 `-lm`（`log()`/`pow()` 熵计算）
- 运行依赖：无第三方库（libcrypto 静态链入，`DT_NEEDED` 仅 `libc.so`）
- 上游亦支持 cryptlib 后端（`secure_random_cryptlib.c`），本配方选用 OpenSSL 后端

## OHOS 适配要点

- **构建系统**：上游只提供 `Makefile.proto`，README 要求打包者复制成 `Makefile` 后取消注释加密后端并改 `PREFIX`。配方改为在 `make -f Makefile.proto` 命令行注入 `CC`（取自 Conan conf，R33）、`CRYPTO_OBJS=secure_random_openssl.o`、`CFLAGS`、`LDFLAGS`，构建系统零补丁
- **`-static` 必须压掉**：上游 `LDFLAGS` 默认含 `LINK_STATIC = -static`，与 Conan 可重定位包冲突；命令行赋值覆盖后产物为 PIE 动态可执行文件（full RELRO + BIND_NOW + 非可执行栈）
- **E051 特权 id syscall**：上游 `drop_privileges()` 无条件调用 `seteuid(getuid())`。鸿蒙内核对非特权进程发起的特权 id syscall 回以**不可捕获**的 SIGSYS（退出码 159），进程被直接终止且任何 signal handler 都拦不住，未打补丁的二进制会在 `secure_memory_init()` 阶段死掉、一行输出都没有。补丁改为仅在 `geteuid() != getuid()`（真正的 setuid 场景）时才调用，是纯 POSIX 写法、不含 `__OHOS__` 平台宏（R8/PF5），对非鸿蒙平台完全透明
- **锁定内存降级**：`mlockall(MCL_FUTURE)`（或 `DISABLE_MLOCKALL` 下的 `mlock`）与 `setrlimit(RLIMIT_CORE, 0)` 在鸿蒙应用沙箱内可能被拒；上游把这两种失败都当作非致命，只打印 `WARNING: using insecure memory.` 并继续，符合鸿蒙沙箱边界，无需改动
- **OpenSSL 3 弃用 API**：`secure_random_openssl.c` 使用低层 Blowfish API（`BF_set_key`/`BF_ecb_encrypt`），3.0 起标记弃用但仍随 libcrypto 提供；配方加 `-DOPENSSL_SUPPRESS_DEPRECATED` 显式声明"确实在用"，而非用 `-Wno-` 掩盖
- **musl 兼容性**：源码为纯 POSIX C，只用 `mmap`/`mprotect`/`mlockall`/`sysconf(_SC_PAGESIZE)`/`setrlimit`/`atexit`，musl 全部提供；异常机制用随源码分发的 `cexcept.h`（C 语言 setjmp 实现），无 C++ 运行时依赖
- **测试**：上游无任何测试套件（`Makefile.proto` 只有 `all`/`install-strip`/`install`/`clean`）；`test_package` 补全 17 个独立检查项，其中 7 项为鸿蒙特有（产物 ABI ×4 + 运行期平台行为 ×3）

## 参考资料

- 上游仓库：<https://github.com/itoffshore/secpwgen>
- 手册页：`secpwgen(1)`（随包安装到 `share/man/man1/`）
- Alpine 打包（同为 1.3，含 `make-openssl.patch`）：<https://pkgs.alpinelinux.org/package/edge/community/x86_64/secpwgen>
