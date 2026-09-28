# udptunnel 1.1 适配笔记

## 编译环境
- 构建系统: autotools（2001 年 autoconf 2.13 / automake 生成，无 AC_CANONICAL_*）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（OHOS SDK sysroot）
- 状态: built

## 编译步骤

1. W0 preflight：零第三方依赖（AC_CHECK_LIB(nsl/socket) 探测 libc 内符号，无外部包），直接通过。
2. 手动探路（build-slot 机动槽）：`CC=clang sh ./configure --prefix=$DEFAULT_PREFIX && make -j1`。
   - configure RC=0（原生运行探测 select/socket/strtol 全过）；
   - make 首败于 `host2ip.c:7 fatal error: rpcsvc/ypclnt.h: file not found`（第一条真实错误）。
3. 补丁后（track-edit + refresh-patch --auto）：make RC=0，产物 `udptunnel`（43KB）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `checking for gcc... no / no acceptable cc found in $PATH` | autoconf 2.13 只找 gcc/cc；设备只提供 clang | 显式 `export CC=clang`（老 configure 支持 CC/CFLAGS 环境变量注入） |
| 2 | `host2ip.c:7 fatal error: rpcsvc/ypclnt.h: file not found` | 1996 年代码把 NIS/YP 当 DNS 之后的兜底；OHOS/musl 无 rpcsvc/ypclnt.h 与 yp_* | 0001 补丁整段删除 YP 兜底（无 NIS 环境该分支本就只会返回 INADDR_ANY，行为等价、无条件删、不带平台宏） |
| 3 | 无 `--help`/版本输出，`-h` 走 usage 且 exit(2) | 1999 年 CLI 惯例 | 0002 补丁（K0 契约）：新增 help() 在 stdout 打印 usage 并 exit(0)，`-h` 与 `--help` 走 help()；错误路径（缺参/未知选项）保留 exit(2) |

## 源码修改

- `patches/0001-host2ip.c.patch`：删 `#include <rpcsvc/ypclnt.h>` + 删 YP 兜底 else 分支（-13/+5）。
- `patches/0002-udptunnel.c.patch`：新增 help()（stdout + exit 0），getopt `case 'h'` 改走 help()，getopt 前拦截 `--help`（+21/-0）。
- 两枚补丁均为平台无关 portability 修改，不含 `__OHOS__` 宏。

## 依赖版本

- 无第三方依赖（零 requires）。
- 构建工具：GNU Make 4.4.1、clang 15.0.4、Conan 2.x（OHOS 适配版）。

## 上游测试清点（R51）

- tar 包 14 个文件，无 tests/ 目录；Makefile.am 只声明 bin_PROGRAMS，无 check_PROGRAMS/TESTS、无 dejagnu/autotest。
- automake 隐式 `check` 目标无可执行内容（make check 空转）。
- 结论：上游无测试套件；消费者断言压在 CLI 契约层（见下）。

## 验证结果

```bash
./udptunnel -h      # usage 打到 stdout，rc=0
./udptunnel --help  # 同上，rc=0
./udptunnel         # 无参：usage 打到 stderr，rc=2（上游错误契约保留）
```

test_package 断言（4 条）：test.c system() 调 `udptunnel --help` 验 rc；test() 内 ①`udptunnel --help` rc=0 ②usage 横幅落 stdout（grep "Usage:"）③无参 rc=2。隧道数据面需真实 UDP/TCP 对端，无法无头验证，按 sff 先例压在 CLI 契约与产物层。

## 注意事项

- 老包（autoconf 2.13）configure 直接可用：无 AC_CANONICAL_* ⇒ 从不调 config.guess，E007/E268 族机制在本包未触发（B 判定面收窄）。
- udptunnel.c 编译仅有 `int*` vs `socklen_t*` 符号警告（1999 年原型），可链接可运行，不做过度修补。

## 对话记录

### 对话 #1

- configure: `CC=clang sh ./configure --prefix=$DEFAULT_PREFIX`（探路 RC=0，秒级；conan create 内由 AutotoolsToolchain 注入等价 CC/CFLAGS 环境）
- 编译: `make -j1`，2 个 .c + 链接，秒级完成
- conan create（G2 干净构建）约 100s；finish W3（setup.sh + build_and_test.sh）约 2min

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/udptunnel | ~43KB | 主命令（-s server / -c client 模式） |
---

**编译结束**: 2026-09-27 03:07
**最终状态**: built
