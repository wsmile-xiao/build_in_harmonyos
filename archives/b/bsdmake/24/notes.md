# bsdmake 24 适配笔记

## 编译环境
- 构建系统: makefile（源码自带 Makefile/GNUmakefile，Apple 发行版；GNUmakefile 依赖 Xcode ReleaseControl 不可用，采用直接 clang 逐 .c 编译 + 链接）
- 编译日期: 2026-09-05
- 编译器: clang（clang version 15.0.4）
- 状态: built

## 编译步骤

bsdmake（Apple BSD make，源自 NetBSD/FreeBSD make）无 configure 脚本。源码自带
Makefile 为 FreeBSD bmake 语法（`.if`/`.include <bsd.prog.mk>`），GNU make 无法直接
解析；GNUmakefile 面向 Apple Xcode 构建环境。实际编译采用上游 Makefile.dist 描述
的等价方式——直接编译 19 个 C 源文件后链接：

```bash
# 编译 19 个源文件（arch.c buf.c cond.c dir.c for.c hash.c hash_tables.c job.c
# lst.c main.c make.c parse.c proc.c shell.c str.c suff.c targ.c util.c var.c）
clang -O2 -I. \
  -D'__FBSDID(x)=' \
  -D'__dead2=__attribute__((__noreturn__))' \
  -DDEFSHELLNAME="sh" \
  -DMAKE_VERSION="5200408120" \
  -c <各 .c 文件>
# 链接
clang *.o -o bsdmake
```

验证：`bsdmake -m <mk 目录> -f Makefile` 可正确解析并执行 makefile 规则。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `<sys/sysctl.h>` 不存在、`sysctlbyname()` 未定义 | FreeBSD 专有接口（pc98 机器类型探测），OHOS 无 sysctl(3) | 补丁 0001：头文件与调用块加 `#ifdef __FreeBSD__` 守卫（仅守卫调用本体，保留 `machine = getenv("MACHINE")` 赋值） |
| 2 | `__FBSDID`/`__dead2` 宏未声明 | FreeBSD `sys/cdefs.h` 专有宏，OHOS 缺失 | 编译参数注入 `-D'__FBSDID(x)='` 与 `-D'__dead2=__attribute__((__noreturn__))'` |
| 3 | `errc()` 链接失败（undefined symbol） | OHOS libc 无 BSD `errc()` | 补丁 0001：等价替换为 `errno = EAGAIN; err(...)` |
| 4 | 首次运行段错误 | main() 中 `machine` 局部变量未初始化——平台守卫若整块包裹 getenv 赋值，非 FreeBSD 分支读到未初始化值 | 守卫只包住 sysctlbyname 调用本体，保留 `machine = getenv("MACHINE")`，`machine` 始终有定义 |

## 源码修改

- `patches/0001-main.c.patch`：3 处修改
  1. `<sys/sysctl.h>` include 加 `#ifdef __FreeBSD__` 守卫
  2. `errc(2, EAGAIN, ...)` 两处替换为 `errno = EAGAIN; err(2, ...)`
  3. `sysctlbyname("machdep.ispc98", ...)` 调用块加 `#ifdef __FreeBSD__` 守卫

## 依赖版本

无第三方库依赖（仅 C 标准库 + POSIX + OHOS 系统头文件）。

## 验证结果

```bash
# test_package 自研 4 组功能断言（conan create 内执行，全部通过）
[test] variable expansion + rule execution passed
[test] dependency graph passed
[test] error propagation passed
[test] MAKESYSPATH sys.mk passed
[test] bsdmake consumer test passed
```

上游 bsdmake-24 源码包无自带测试套件（无 unit-tests/regress/autotests 目录），
依据测试强制红线由 test_package/test.sh 自研 4 组断言覆盖核心功能。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（application 类型，手工编译 + 链接 bsdmake） |
| conandata.yml | 官方源 URL + sha256 + 补丁声明 |
| commands.json | 命令行工具声明（R38） |
| patches/0001-main.c.patch | OHOS 平台适配补丁 |
| test_package/ | 消费者测试（4 组功能断言） |

## 注意事项

1. 补丁引入 `#ifdef __FreeBSD__` 平台守卫属 R8 例外：OHOS 无 sysctl(3) 等 POSIX
   等价物，且仅涉及 FreeBSD/pc98 专用机器探测代码，非空壳 stub。
2. conanfile.py 通过 `self.conf.get("tools.build:compiler_executables")` 获取编译器
   （R33），未依赖 shell 环境变量。
3. 首次提交后 W3 本地 CI 因本分支未提交变更（`git diff origin/main...HEAD` 为空）
   回退 full 模式扫描，误报 main 上历史遗留文件 `archives/u/util-linux-login/2.42.2/.ci-trigger`；
   提交变更后走 incremental 模式通过。

---

**编译结束**: 2026-09-05 13:09
**最终状态**: built
