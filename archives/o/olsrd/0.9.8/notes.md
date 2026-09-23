# olsrd 0.9.8 适配笔记

## 编译环境
- 构建系统: makefile（手写 Makefile/Makefile.inc，非 autotools；顶层 `make` 出守护进程，`make libs` 出插件）
- 编译日期: 2026-09-05
- 目标平台: OpenHarmony / HarmonyOS PC aarch64（真机原生构建，HongMeng Kernel 1.12.0 aarch64）
- 编译器: clang 15.0.4（OHOS NDK，默认 target aarch64-linux-ohos + musl sysroot）
- 构建工具: GNU Make 4.4.1 / bison 3.8.2 / flex 2.6.4
- 状态: built（本地 W3 验证通过，待 PR）

## 编译步骤（conan 配方内等效命令）
```bash
# 1. 守护进程 olsrd（OS 必须强制 =linux，否则 guess_os.sh 对 OHOS 返回 UNKNOWN）
make OS=linux CC=clang EXTRA_CPPFLAGS="-D__MUSL__" NORPATH=1
# 2. 插件集（Linux 默认集 - pud；pud 依赖 gpsd 3.18 老 API，gpsd/3.26 不兼容，排除）
make libs OS=linux CC=clang SUBDIRS="arprefresh bmf dot_draw dyn_gw dyn_gw_plain httpinfo \
  info jsoninfo mdns mini nameservice netjson poprouting p2pd pgraph quagga secure \
  sgwdynspeed txtinfo watchdog" EXTRA_CPPFLAGS="-D__MUSL__ -I<openssl>/include" NORPATH=1
# openssl 头/库通过 CPATH/LIBRARY_PATH 提供（secure 插件 -lssl -lcrypto 链接）
```
- 依赖注入：openssl/3.0.16 由 conan requires 提供，`-I/-L` 走 `CPATH`/`LIBRARY_PATH`（环境变量可穿透子 make 与 clang 驱动）。
- 安装路径隔离：`NORPATH=1` 禁止把 `/usr/local/lib` rpath 烤进产物（E524/R49 精神）。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `src/gateway.c` 等: `linux/socket.h:23 error: redefinition of 'sockaddr_storage'`（E091/E119 命中） | OHOS NDK 头组织：`linux/socket.h` 由 bionic 工具生成、无条件定义 `sockaddr_storage`；而 musl `sys/socket.h` 也定义同名结构。`sys/socket.h` 内建协调钩子 `#ifdef __MUSL__`（仅此一处使用 __MUSL__） | 编译期注入 `-D__MUSL__`：musl `sys/socket.h` 不再重复定义并由内核头统一提供。非源码补丁，属 sysroot 预留钩子 |
| 2 | `src/linux/kernel_routes_nl.c:164` `error: incompatible pointer to integer conversion initializing 'int'` | `struct msghdr` 位置初始化第 5 位 `msg_flags`(int) 用 `NULL`((void*)0)；clang 对 int 初始化 void* 为硬错误 | 源文件 `NULL` → `0`（补丁 1） |
| 3 | `src/cfgparser/oparse.c fatal: 'oparse.h-tmp' file not found` | bison ≥3.x 的 `-d -o xxx.c-tmp` 生成 `xxx.h-tmp` 且 `.c` 内嵌 `#include "xxx.h-tmp"`；上游规则 sed 只改 #line，mv 后头文件引用悬空（上游按老 bison 行为编写） | 补丁 `src/cfgparser/local.mk`：bison 生成后 sed 增加把 `.h-tmp` 引用改写为最终 `.h`（补丁 2） |
| 4 | `lib/pud` 无法用 gpsd/3.26 编译：`fixsource_t` 重定义 + `gps_data_t.status/online/fix.time/fix.altitude/separation` 及 `PRN[]/elevation[]` 旧数组全部被 gpsd 3.20+ 移除 | olsrd 0.9.8 停更，pud 仍用 gpsd 3.18 前客户端 API；gpsd/3.26 客户端 API 破坏性变更 | **排除 pud 插件**（可选插件），构建范围裁剪为 Linux 默认集减 pud；gpsd 不再作为依赖 |
| 5 | `make install: install: No such file or directory` | OHOS 默认 PATH 无 `install`（在 /bin、/system/bin） | 配方/安装阶段 PATH 前置 `/bin:/system/bin`；staging 安装验证 exit=0 |

## 源码修改
- `src/linux/kernel_routes_nl.c`：`struct msghdr` 初始化的 `NULL`(msg_flags 位) → `0`
- `src/cfgparser/local.mk`：bison 规则 sed 增加改写 `oparse.h-tmp` → `oparse.h`（兼容 bison 3.x）

## 依赖版本
- openssl/3.0.16（仅 secure 插件需要；可消费，ohpcd 已发布二进制）
- tool_requires: flex/2.6.4.2、bison/3.8.2（cfgparser 生成器；ohpcd 已发布）
- 系统库 libm/libdl/librt/libpthread → OHOS libc（产物仅 NEEDED libc.so）
- gpsd/3.26：**排除使用**（pud 插件排除后不再需要）

## 验证结果
```bash
# 守护进程 + 19 插件编译通过（err=0）
# 安装 staging（DESTDIR=$TEST_PREFIX, LDCONFIG=true）exit=0
# ./olsrd -h 真机执行输出 "*** olsr.org - 0.9.8 ... ***" + usage（-h 后进程不退出，需 timeout 终止）
# 产物: ELF 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), NEEDED 仅 libc.so
```

## 上游测试清点
- 上游 tarball **无自动化测试入口**：无 `make check`/`make test`/ctest/`tests/` 目录（全树检索为空）。
- 真实可执行验证入口：`./olsrd -h`（输出版本+usage；真机实测通过）。插件验证以 conan test_package 中 dlopen 方式执行。

## 注意事项
- 上游版本串为 `0.9.8-git_0000000-hash_...`（VERS 0.9.8 + git 占位）。
- 守护进程默认需 root + 网卡才能实际建网；测试仅做静态/启动级验证。
- 配方必须强制 `OS=linux`（guess_os.sh 对 OHOS 判 UNKNOWN，会落 win32 分支）。
## R47 语言预检：工具误判说明（复核）

`lang-preflight` 对完整 tarball 返回 `detected_language=java`（exit 2）。经核验为
**工具边界假阳性**，olsrd 属 C 流水线，理由与证据：

- 触发项是 `if names & {"build.gradle","pom.xml"}` 的**全树扫描**，且该 java 规则排在
  "顶层 Makefile → c/cpp" 之前，故只要树里存在任意 Java manifest 即先判 java。
- 命中的 `build.gradle` 全部位于 `lib/info.java/**`（olsrd INFO 插件的**独立 Java 客户端库**，
  非本包产物）与 `lib/pud/wireformat-java`；`find *.java`=152 个中 148 个在 `lib/info.java/`、
  4 个在 `lib/pud/wireformat-java`，二者均不在构建范围。
- 顶层构建系统是 C 的 `Makefile`；本 conanfile `_PLUGINS` 全为 C 插件（含 C 版 `info`，
  **排除 `pud`**），`make`/`make libs` 不编译任何 Java。产物 `olsrd` 为纯 C musl ELF。
- 处理：不改框架 detector、不伪造门禁，按实际构建目标（C）继续适配；此处留证供审阅判断。

## W0 依赖复核（本轮 feat/olsrd-0.9.8 重跑）

`conan download <ref> -r=ohpcd --only-recipe` 全部 exit=0（本地缓存命中，R35 口径）：
`openssl/3.0.16` `flex/2.6.4.2` `bison/3.8.2` `m4/1.4.19`（flex 传递依赖）。
`gpsd/3.26` 在仓但**不消费**（pud 已裁剪）。无强制依赖缺失，未触发 R36 阻塞。
---

**编译结束**: 2026-09-05 18:07
**最终状态**: built
