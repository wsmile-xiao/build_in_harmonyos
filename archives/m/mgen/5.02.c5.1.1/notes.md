# mgen 5.02.c5.1.1 适配笔记

<!-- Adapted for HarmonyOS PC platform (arm64) -->

## 版本说明

- 配方版本：`5.02.c5.1.1`；上游：NRL MGEN release **V5.1.1**
  （https://github.com/USNavalResearchLaboratory/mgen）。
- 版本号映射：`include/mgenVersion.h` 中 `MGEN_VERSION "5.1.1"`，
  `VERSION.TXT` 顶条目为 5.02c（V5.1.1 是 5.02c 代码基线上的发布增量，
  含 win64 timeval 修复等 27 个提交）。Debian 源码包版本为
  `5.02.c+really5.1.1`，配方版本号 `5.02.c5.1.1` 与其对应。
- 上游 protolib 子模块：V5.1.1 固定 gitlink
  `726486395910740a02ff3137752d1a1c82cb3e81`（`.gitmodules`），GitHub tag
  tarball 不含子模块内容，`source()` 从官方 GitHub 归档二次获取，
  解压到源码根 `protolib/`（Makefile 期望的 `../protolib` 布局）。

## 编译环境

- 构建系统：makefile（`makefiles/Makefile.linux`，无 configure）
- 编译器：clang/clang++（Conan conf `tools.build:compiler_executables`，
  R33，不依赖 shell 环境变量）
- 状态：built（本地工作树完成，待 HMBS 真机预检实测）
- 产物：`mgen`（主流量发生器）、`mpmgr`（共享内存 payload 管理器）

## 编译步骤

1. 获取 mgen V5.1.1 tarball（strip_root）+ protolib 固定提交 tarball
   （解压到 `protolib/`）。
2. 构建时去掉可选 pcap：`build()` 内对 `makefiles/Makefile.linux`
   做纯文本替换，去掉 `-DHAVE_PCAP` 与 `-lpcap`（不用 .patch 文件：
   tag 包字节与 git 检出存在差异，hunk 上下文对不上会导致
   `source file is different` 应用失败；且只改 mgen 自有 Makefile，
   不用 make 命令行覆盖，避免命令行变量泄漏到 protolib 子 make 破坏其
   自有 SYSTEM_HAVES/SYSTEM_LIBS）。
3. `make -f Makefile.linux -j1 CC=<conan-cxx> ...`（`makefiles/` 目录）：
   先以子 make 构建 `protolib` 的 `libprotokit.a`，再链接 `mgen`/`mpmgr`。
4. `package()` 将 `makefiles/mgen`、`makefiles/mpmgr` 复制到 `bin/`。

## 依赖版本

- 本配方**零外部依赖**（OHOS 适配主动去掉可选的 libpcap）：
  - 上游 `HAVE_PCAP` 全部被 `#ifdef` 保护（`mgenPattern.cpp` 的 CLONE
    pattern、`OpenPcapDevice` 等），去掉后核心流量模式
    PERIODIC/POISSON/BURST/JITTER 不受影响，仅 CLONE pcap 回放不可用；
  - protolib 自身从不需要 pcap（其 `Makefile.linux` 仅链接 `-ldl -lrt`）。
- 不需要 libxml2：protolib `Makefile.common` 虽写 `-lxml2`，但
  `protoXml.cpp` 不在 `libprotokit.a` 的 `KIT_SRC` 中，且 mgen 链接行不
  使用 protolib 的 `LIBS`，静态归档不做链接。

## 上游测试审计（no_tests）

详见 `test_package/MANIFEST.yml`。结论：上游 V5.1.1 无任何自动化测试
（无 tests/ 目录、无 check/test make 目标、无 TESTS/check_PROGRAMS、
无 ctest/gtest/pytest 接线；Debian 构建亦不跑测试）。
`build()` 因此不调用上游测试，直接输出
`HMBS_UPSTREAM_TEST_RESULT(status=no_tests, discovered=0)`；
`test_package` 以 8 个运行时消费者用例验证打包二进制。

## test_package 设计

`test_mgen.sh`（POSIX sh，无网络、无外部服务）：
1. `mgen help` 输出非空（真实启动证据）；
2. 输出含 `mgen: version 5.1.1`；
3.–6. 输出含 `input <scriptFile>` / `output <logFile>` /
   `convert <binaryLog>` / `interface <interfaceName>`；
7. `mpmgr` 存在且可执行；
8. 未知命令 15 秒内退出（后台运行 + `kill -0` 轮询 + 超时 kill，
   防 dispatch 循环挂起；退出码只记录不硬断言）。
全部通过输出 `HMBS_TEST_PACKAGE_RESULT(discovered=8)`，任一失败退出 1。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub tag 包不含 protolib | protolib 是 git submodule，codeload 归档排除子模块 | `source()` 二次 `get()` 官方 protolib 固定提交归档到 `protolib/` |
| 2 | Makefile 硬编码 `CC = g++` | 上游面向 Linux GCC | make 命令行覆盖 `CC=<conan-cxx>`（命令行变量优先于文件赋值，且传递给子 make） |
| 3 | 真机预检卡在 `libpcap -> bison/flex -> m4/1.4.19`，`configure[139]: /data/service/hnp/bin/bash: inaccessible or not found`（error 127） | conancenter 的 autotools 版 libpcap 在 OHOS worker 上必须从源码构建 m4，而其 configure 要重 exec hnp bash；该 bash 在新真机（47.242.172.160）不可用。且 HAVE_PCAP 上游本就是可选特性 | 加补丁去掉 `-DHAVE_PCAP`/`-lpcap`，配方删掉 `libpcap/1.10.6` 依赖（零外部依赖）。只禁用 CLONE 回放，核心功能无损；补丁只改 mgen 自有 Makefile，不泄漏到 protolib 子 make |
| 4 | 真机 `linuxRouteMgr.o` 编译失败：`linux/socket.h:23: error: redefinition of 'sockaddr_storage'`（与 `sys/socket.h:377` 冲突，经 `zebraRouteMgr.h` → `linux/netlink.h` 引入） | OHOS musl sysroot 的内核 UAPI `linux/socket.h` 无条件定义 `sockaddr_storage`，与 musl `sys/socket.h` 双定义同 TU 必冲突（ace/gupnp/busybox 同类 E119）；protolib netlink 代码仅用 `sockaddr_nl`/`nlmsghdr`，不需要内核版该结构 | `build()` 内纯文本替换隐藏内核版定义：凡含 `<linux/netlink.h>` 的 protolib 源码，在该 include 前加 `#define sockaddr_storage __hmbs_kernel_sockaddr_storage`、在 `rtnetlink.h` 后 `#undef`；保留 netlink 功能、无平台宏、无功能删减（不用 .patch 文件，避免 tag 包字节差异导致 hunk 失败） |

## 真机风险（待预检证实）

- protolib `linuxRouteMgr.cpp` 等 Linux 专有网络代码在 OHOS/musl 下的
  编译兼容性（未知，需真机日志）。
- `-lrt`、`-ldl` 在 OHOS 工具链的可用性（rtklib/masscan 有 `-lrt` 链接
  先例，预期可行；失败则以补丁或 `SYSTEM_LIBS` 覆盖处理）。
- `HAVE_GPS` 默认开启：`GPSSubscribe(NULL)` 无 GPS 时返回空句柄，
  Linux 侧无 GPS 也可运行；若 OHOS 侧阻塞/崩溃，备选关闭该宏。

## 验证结果

- 本轮：工作树完成，未提交；`conan create` 与测试计数待 HMBS 真机预检
  实测回填（不估算、不照抄）。
- `mgen help` 的版本横幅与用法文本已从源码静态确认
 （`mgenApp.cpp: Usage()` + `mgenVersion.h`）。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/mgen | 主流量发生器 CLI |
| bin/mpmgr | 共享内存 payload 管理器 CLI |
