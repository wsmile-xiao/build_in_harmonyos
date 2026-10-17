# macutils 2.0b3 适配笔记

## 编译环境

- 构建系统: 手写递归 makefile（无 configure；9 个 makefile，顶层只向子目录传 `CF` 特性宏）
- 编译日期: 2026-09-26
- 编译器: OHOS clang 15（`/data/service/hnp/bin/clang` → `aarch64-unknown-linux-ohos-clang`），归档器 `llvm-ar`
- Profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS / arch=armv8 / Release），本机为 x86_64 runner
- 依赖: 无
- 状态: published（conan-verify G1-G4/L2/L4/L5 通过）

## 源码

- 上游: <https://github.com/dgilman/macutils>（Debian 源码入库；无 release tag）
- 钉住提交 `920f51fed5068086713f069801eb094fa36b1011`：Debian 2.0b3-16 源码 + debian #903505 cross patch，
  其后的 `4b3132c` 才把版本号改成 2.1，因此它是 2.0b3 的最终状态
- sha256 `386f02a9ee6e26fd85613d27e9b7380cbe06bd2a6dc77b9b9d214c3544c1651f`（github archive 与 codeload 同一文件）

## 编译步骤

```bash
make CC=<clang> AR=<llvm-ar> "CC_FOR_BUILD=<clang> -static" \
     "CF=-std=gnu89 -Wno-deprecated-non-prototype -DTYPES_H -DDIRENT_H -DTERMIOS_H -DNODOT -DAPPLEDOUBLE"
```

`CC`/`AR`/`CC_FOR_BUILD` 从 make 命令行经 MAKEFLAGS 传到各子 make；编译器取自 Conan conf
`tools.build:compiler_executables`（R33，不读裸 shell 变量），`llvm-ar` 在 clang 同目录或其解析后的 NDK 目录查找。
上游 makefile 无 DESTDIR / install 前缀，`package()` 按上游 `install` 目标列出的 7 个工具手工复制。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `makecrc.c:40: error: return type defaults to 'int'` | 1992 年 K&R 代码（隐式 int、旧式定义），新编译器默认 C99+ 视为错误 | `CF` 加 `-std=gnu89`；`-Wno-deprecated-non-prototype` 压掉约 1000 条旧式定义告警 |
| 2 | `crc/makefile` 写死 `cc -O -o makecrc` 与 `ar r` | 构建期生成器 makecrc 要在构建机上运行，生成 6 个 CRC 表 .c；设备无 `cc`/`ar` | 补丁 0004 改为 `$(CC_FOR_BUILD)`（默认 `$(CC)`）与 `$(AR)`；配方传 `CC_FOR_BUILD=<clang> -static`：AArch64 CI 原生可跑，x86_64 runner 经 qemu-user binfmt 也能跑（动态产物缺 `/lib/ld-musl-aarch64.so.1` 跑不了） |
| 3 | `transname.c:93: use of undeclared identifier 'DIRSIZ'` | 只认 4.2BSD `MAXNAMLEN` 或 SysV `DIRSIZ`，musl 两者都没有 | 补丁 0005：`#elif defined(DIRSIZ)`，再兜底 `<limits.h>` 的 `NAME_MAX`（特性检测，不用平台宏） |
| 4 | `binhex.c:36: error: incompatible integer to pointer conversion ... get_rdfileopt()`（frommac 同类） | 缺原型的 `char *get_rdfileopt()`/`get_wrfileopt()` 被隐式声明为返回 int；LP64 上指针会被截断，clang 15 直接报 `-Wint-conversion` 错 | 补丁 0001-0003：包含上游已有的 `rdfileopt.h` / `wrfileopt.h`；剩余隐式声明逐个核对均为返回 int/void 的函数（`readline`/`do_query`/`gethuffbyte` 等），无截断风险 |
| 5 | 手工 `-static` 构建 + qemu 测试全绿，`conan create` 却报 `ld.lld: error: undefined symbol: rindex` | 上游 CF 带 `-DBSD`，`hexbin/globals.h` 在 BSD 分支用 `rindex`；OHOS `libc.so` 不导出 `rindex`（`libc.a` 有，`<strings.h>` 也不声明），静态探针掩盖了问题 | 配方 CF 去掉 `-DBSD`（上游说明其含义是 "if you are on a BSD system"），走上游自带 POSIX 分支：`strrchr`、`<time.h>`、`memcpy/memset`，零补丁；沉淀草稿 `E544-draft-6EE2`（libc.a 比 libc.so 多 380 个非下划线符号） |

`patches/` 无 `__OHOS__` 等平台宏；配方未注入 `-D__OHOS__`。

## 源码修改

| 补丁 | 文件 | 修改 |
|---|---|---|
| 0001 | `binhex/binhex.c` | `#include "../fileio/rdfileopt.h"` |
| 0002 | `comm/frommac.c` | `#include "../fileio/wrfileopt.h"` |
| 0003 | `comm/tomac.c` | `#include "../fileio/rdfileopt.h"` |
| 0004 | `crc/makefile` | `CC_FOR_BUILD ?= $(CC)`、`AR ?= ar`；makecrc 用 `$(CC_FOR_BUILD)`，libcrc.a 用 `$(AR)` |
| 0005 | `util/transname.c` | `FNAMELEN`：`MAXNAMLEN` → `DIRSIZ` → `NAME_MAX` |

## 上游测试清点（R51）

- 顶层 11 项：`README binhex comm crc doc fileio hexbin macunpack makefile man mixed util`，无 `test/`、`tests/` 目录
- 9 个 makefile 的目标只有 `all/clean/clobber/lint/install/distr`（及各程序/对象规则），无 `check`/`test`
- 无 CMake/automake/python，ctest/TESTS/pytest 注册数均为 0
- 结论：上游无自动化测试，**N = 0、N′ = 0**；功能覆盖由 `test_package/` 的消费者用例补齐

## 验证结果

### 1. conan-verify（W3 同源，x86_64 runner）

`ohc-run.py conan-verify macutils 2.0b3` → G1/G2/G3/G4/L2/L4/L5 通过。
test_package：消费者 `test_macutils` 已用 OHOS 工具链编译链接；`test()` 校验 7 个工具都在包内，
因构建机非 AArch64 打印 `Skipping target execution on a non-AArch64 build machine`（动态产物在 x86 上缺 loader）。

### 2. 鸿蒙特有消费者用例 — 同源 .o 静态重链 + qemu-aarch64 实跑

交付件是动态链接（`interpreter /lib/ld-musl-aarch64.so.1`），x86 上跑不了。做法：复制 conan 缓存构建目录，
只删除 7 个工具二进制，以 `CF=... -static` 重跑 make（make 只重新链接，`.o` 不重编）；
消费者用 test_package 构建目录里的 `test_macutils.c.o` 以 `-static` 重链。

```text
$ PATH=/root/tmp/relink/bin:$PATH ./test_macutils_static w
OK: macunpack extracted 2 PackIt entries, Mac Roman name -> Cafe_Menu
OK: macunpack rejected corrupted archive (exit 1)
OK: binhex output decoded independently (3037 bytes, 3 CRCs valid)
OK: hexbin restored the data fork byte-for-byte
OK: hexbin detected the tampered .hqx (exit 1)
OK: macstream -> macsave round trip is byte-identical
ALL MACUTILS CONSUMER TESTS PASSED
exit=0
```

（stderr 中的 `CRC error in file ...` / `CRC mismatch ...` 来自两条故意损坏输入的负向用例。）

反向对照：把 `binhex` 换成改写输出第 5 行一个字符的包装器 → `FAIL: BinHex data fork differs from input`，exit=1。

跨架构一致性：同一用例在 x86_64 原生构建的工具上同样 6/6 通过，且 `payload.hqx`、`stream.bin`、
`Cafe_Menu.info` 与 aarch64 产物逐字节一致（aarch64 的 `char` 为无符号，x86 为有符号，结果一致）。

**说明**：qemu 跑的是同源 `.o` 的静态重链副本，**不等于交付的动态产物已实跑**；
交付产物由 AArch64 CI 的 `conan create` → `test_package` `test()` 执行（本地未实跑、由 CI 执行）。

### 用例统计

| 类别 | 数量 |
|---|---|
| 上游测试 N / N′ | 0 / 0（上游无测试） |
| test_package 消费者用例 | 6（全部在 `test_macutils.c`，qemu 实跑 6/6） |
| 鸿蒙特有测试 | 6（同上，由 `test_package/conanfile.py` `test()` 在 AArch64 上执行） |

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/macunpack` | 解 StuffIt/PackIt/Compactor/DiskDoubler 等 Mac 归档 |
| `bin/hexbin`、`bin/binhex` | BinHex 4.0（及 .dl/.hcx/.mu 等）解码 / 编码 |
| `bin/macsave`、`bin/macstream` | MacBinary 流 ↔ 文件 |
| `bin/tomac`、`bin/frommac` | XMODEM/YMODEM 串口收发 |
| `share/man/man1/*.1` | 上游手册页 |
| `licenses/README` | 版权说明（README 末尾："use and redistribution of all such code is explicitly allowed"） |

## 注意事项

- 同一上游版本若需再修适配问题，版本号用 `2.0b3.N`（R37）。
- `tomac`/`frommac` 需要串口终端（termios），未纳入自动化用例。
---

**编译结束**: 2026-09-26 23:21
**最终状态**: published
