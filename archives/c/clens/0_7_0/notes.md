# clens 0_7_0 适配笔记

## 编译环境
- 构建系统: makefile（上游 Makefile 为 OpenBSD bsd.lib.mk；GNU 平台走 GNUmakefile。配方不依赖其 make 规则，直接编译选定 TU + llvm-ar）
- 编译日期: 2026-09-07
- 编译器: clang (OHOS NDK 15.0.4, target aarch64-linux-ohos)
- 状态: built

## 上游概况

clens（https://github.com/conformal/clens，ISC）是 Conformal 的 OpenBSD API
兼容层库，供 OpenBSD 代码移植到其它系统。tag `CLENS_0_7_0` 源码共 10 个 TU：

| TU | 提供 API | OHOS libc (musl) 是否原生提供 |
|----|----------|------------------------------|
| clens.c | clens_verstring / clens_version | 否（clens 独有） |
| strtonum.c | strtonum | 否 |
| fmt_scaled.c | fmt_scaled / scan_scaled | 否 |
| fparseln.c | fparseln | 否 |
| strlcpy.c / strlcat.c | strlcpy / strlcat | **是**（`string.h` 实测声明） |
| arc4random_buf.c / arc4random_uniform.c | arc4random_buf / arc4random_uniform | **是**（`stdlib.h` 实测声明 arc4random/arc4random_buf/arc4random_uniform；且 Linux 路径无条件 `#include <bsd/stdlib.h>` 需 libbsd） |
| fgetln.c | fgetln | **是**（`stdio.h` 实测声明） |
| glob.c | glob / globfree | **是**（`glob.h` 实测存在；且 glob.c 用 u_char/u_short/u_int 旧 BSD 类型，musl 需 _BSD_SOURCE 仍不完整） |

## 适配决策（核心）

**裁剪规则：OHOS libc 已提供的符号不编 shim TU，只编真实增量 TU。**
配方只编译 `clens.c strtonum.c fmt_scaled.c fparseln.c`，
arc4random_buf/arc4random_uniform/strlcpy/strlcat/fgetln/glob 六个 TU 编掉。
被裁掉的 API 在消费者侧直接由 libc 提供，**API 面无损失**（test_package
已同时断言两组符号：库内 4 TU 的 API + libc 的 strlcpy/arc4random/glob）。

选择该方案而非"全量 10 TU + libbsd"的原因：
1. 制品仓 `libbsd`/`libmd` 未发布（PF4 探针实测：`conans/search?q=libbsd/*`
   返回空集；对照 zlib 正常返回），R36 禁止捎带适配依赖；
2. OHOS musl 原生提供 arc4random 族，libbsd 在 OHOS 上没有存在必要——
   Homebrew 的 libbsd 依赖是 Linux/glibc 特例（glibc 无 arc4random）；
3. 全量 10 TU 在 OHOS 上编译 arc4random_buf/uniform 会因
   `<bsd/stdlib.h>` 缺失直接失败，glob.c 会因 u_int/u_short 失败，
   strlcpy/strlcat/fgetln 会与 libc 符号冗余。

零补丁、零平台宏、零对 tarball 的修改：裁剪发生在配方 build() 的 TU 列表
（R8/PF5 天然合规）。

## 编译步骤

```bash
# 探索验证（设备原生 clang，即 CI profile 的 compiler_executables）
/data/service/hnp/bin/clang -Wall -Werror -O2 -I include/clens -c \
  src/{clens,strtonum,fmt_scaled,fparseln}.c -o <tu>.o
/data/service/hnp/bin/llvm-ar rcs libclens.a <4 个 .o>
```

同一命令集在 OHOS NDK clang（--target=aarch64-linux-ohos --sysroot=...）
交叉模式下逐一验证通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | arc4random_buf.c 编译报 `'bsd/stdlib.h' file not found` | 上游 Linux 路径依赖 libbsd；制品仓未发布 libbsd | 裁剪该 TU：OHOS musl `stdlib.h` 原生提供 arc4random 族（实测 sysroot 头文件 + 消费者链接探针验证） |
| 2 | glob.c 编译报 unknown type `u_char`/`u_short`/`u_int`（含 `-D_BSD_SOURCE -D_GNU_SOURCE` 后仍报 u_short） | musl 的 BSD 类型可见性与 OpenBSD 头文件层级不同 | 裁剪该 TU：OHOS libc 原生提供 `glob()`（`glob.h` 实测存在，消费者探针 glob 调用通过） |
| 3 | 消费者探针 `tmpfile()` 返回 NULL 导致 core dump | OHOS 设备无 /tmp（E002），tmpfile 依赖不可写默认路径 | test.c 改用 `TMPDIR`/当前目录显式文件，非库缺陷 |
| 4 | GitHub `github.com/.../archive/...` 直连被重置（SSL_ERROR_SYSCALL），且 CI worker 对 github.com 直连与 gh-proxy.com 镜像均超时（#41834 失败日志实证） | 设备与 CI worker 出网限制 | 配方源 URL 改用官方 `codeload.github.com` 端点（同内容字节级 SHA256 `0cc18155…` 实测一致；仓库 156+ 合并配方同策略，如 abbtr/accel-config），显式 `filename: clens-0_7_0.tar.gz` |

## 上游测试用例申报表（R51 三步法第 1 步）

- 清点方法：`find . -iname '*test*' -o -iname '*check*'`（无命中）；
  `Makefile`/`GNUmakefile` grep `check|test`（无目标）；`make -n check` →
  `No rule to make target 'check'`；`config/` 目录仅平台 makefile 片段、
  RPM spec 与 debian 打包，无测试。
- `N_static`（上游静态声明用例数）= **0**（上游确无测试，清点证据如上）
- `N_registered`（构建系统注册数）= 0（无 check/test 目标）
- `N_executed` = 0；`N_pass` = 0；`N_fail` = 0；`N_skip` = 0
- `N_consumer`（新增消费者测试）= 1 个测试程序（test.c，29 处断言）

## 依赖版本

- 构建依赖：无（libc 即 OHOS sysroot）
- 运行时依赖：无

## 验证结果

```text
conan create（profile ohos-aarch64, os=OHOS clang15 armv8）：
  - G2 干净源码构建通过，4 个 TU 编译 + libclens.a 归档成功
  - test_package 编译链接 libclens.a + 头文件全量安装
  - ./test_clens 运行：29/29 断言通过，"all checks passed" exit 0
```

conan-verify G0-G5/L2/L4/L5 与 finish W3 本地 CI 模拟（setup.sh +
build_and_test.sh，含 JC/KC/L0 门禁）均已通过，日志见 reports/。
