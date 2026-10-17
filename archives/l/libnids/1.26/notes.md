# libnids 1.26 适配笔记

## 编译环境

- 构建系统: autotools（configure + make，老式 autoconf）
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15（HarmonyOS PC 真机）
- 状态: built（待真机预检回填证据）

## 上游信息

- 官方主页：https://libnids.sourceforge.net/
- 官方源码：https://github.com/MITRECND/libnids（tag 1.26）
- 源码包：libnids-1.26.tar.gz（146172 字节，sha256 3f3e9f99a83cd37bc74af83d415c5e3a7505f5b190dfaf456b0849e0054f6733）
- 源码结构：configure + configure.in + Makefile.in + src/ + samples/ + doc/，共 53 个文件
- 许可证：GPL-2.0-only

## 编译步骤

1. `get` 解压官方 tag 包（strip_root）。
2. `generate`：AutotoolsToolchain 注入 `-Wno-error=implicit-function-declaration -Wno-error=int-conversion -D_DEFAULT_SOURCE`，配置参数 `--build/--host=aarch64-unknown-linux-gnu --prefix=/ --disable-dependency-tracking --disable-libnet --disable-libglib`，shared 时追加 `--enable-shared`。
3. `build`：改写 configure 中 `umask 077` 为 `umask 022`（HMDFS 兼容）；HMBS_AUTOCONF_MKTEMP_FALLBACK=1 时挂载 mktemp shim；经 device shell 执行 configure；`make -j1`。
4. `package`：`make install install_prefix=<package_folder> -j1`；shared 时补 `libnids.so -> libnids.so.1.26` 符号链接（不支持 symlink 时复制）；static 时清除残留 `.so*/.la`；复制 COPYING 到 licenses。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 旧版 config.guess 无 OHOS 分支 | 不打补丁改生成文件，用 `--build/--host` 显式三元组绕过探测（E007 fallback 口径） |
| 2 | configure 生成 config.status 失败 Permission denied | HMDFS 下 `umask 077 && mktemp -d ./conf*` 产生属主不可写目录 | 构建时将 configure 中 `umask 077` 改写为 `umask 022`；复用 HMBS 注入的可写 TMPDIR |
| 3 | 可选依赖过重 | libnet（raw 注入）与 glib2（多进程）非核心必需 | 路径 A 关闭两者，仅保留 libpcap/1.10.6；killtcp 主动断流功能随之禁用，已在 README 声明 |
| 4 | 老 C 代码在 clang 15 下 implicit-function-declaration 报错 | 上游代码年代久远 | extra_cflags 降级为警告，不修改上游源码 |
| 5 | configure 报 `machine 'aarch64-unknown' not recognized` | 自带 config.sub 为 2000-12-15 版，早于 aarch64 支持（约 2012），`aarch64-unknown-linux-gnu` 无法规范化 | 构建时用纯 Python 给 config.sub 的两处 CPU 列表补 `aarch64/aarch64be`（构建期改写，不进补丁、不改 tarball/sha256，无新增 tool_requires）；显式 `--build/--host` 已绕过 config.guess，无需动 config.guess |
| 6 | configure 报 `C compiler cannot create executables`（exit 77），`checking for aarch64-unknown-linux-gnu-gcc... /data/service/hnp/bin/clang` 之后 | 手写 `self.run(sh configure)` 未带 `env="conanbuild"`，裸 clang 缺工具链的 `--target/--sysroot` 与 AutotoolsDeps 的 libpcap 标志，conftest 链接失败；且 generate() 缺 AutotoolsDeps | configure/make/install 三处手写调用补 `env="conanbuild"`（cursynth 1.5 同机先例），`make -j1` 改走 `Autotools.make`，generate() 增 `AutotoolsDeps`；configure 失败时转储 config.log 尾部便于下轮诊断 |
| 7 | 同上错误在补 `env="conanbuild"` 后原样复现（第 3 次同指纹） | `env="conanbuild"` 只聚合 profile buildenv，不含工具链 CC/CFLAGS/LDFLAGS（证据：两轮日志均为 PATH 搜索行 `checking for aarch64-unknown-linux-gnu-gcc...`，说明 CC 为空）；真正 source 工具链脚本的是 Autotools helper，手写调用必须显式 source | 手写命令内显式 `. conanautotoolchain.sh` + `. conanautotoolsdeps.sh`（`[ -f ]` 守卫，路径取 generators_folder），保留行内 CONFIG_SHELL 覆盖；configure 前打印 HMBS_DIAG_CC/CFLAGS/LDFLAGS/LIBS 四行；config.log 转储改为精准摘录（失败 conftest 命令 + error 行，限 30 行防截断） |
| 8 | configure 报 `cannot run /data/service/hnp/bin/bash .../config.sub`（本轮新指纹；HMBS_DIAG_CC 已正常，toolchain 已 source 成功） | 上轮 `VAR=val [ -f ] && . tc` 前缀只作用于单个 `[` 命令、不会持久化，且 conanautotoolchain.sh 会重新导出 profile buildenv 的坏 SHELL（ohos-aarch64 第 32-33 行，HMDFS 上 getcwd 失败，myman DRAFT-6487 同根因）；configure 内部用 SHELL 跑 config.sub | build()/package() 全局 os.environ 覆盖 CONFIG_SHELL/SHELL=/bin/sh；configure 命令改 export 形式、source 之后再 export /bin/sh 双保险，解释器硬编码 /bin/sh（myman 同款）；package 的 make install 同步加前缀 |
| 9 | configure 报 `/data/service/hnp/bin/clang: inaccessible or not found`（SHELL 修复后新指纹；HMBS_DIAG_SHELL=/bin/sh、target 解析已过）+ source 阶段 github 直连超时重试 | 工具链声明的绝对 CC 在本轮 worker 上经 /bin/sh  exec 失败（toybox sh 报 inaccessible）；下载日志有 ConnectTimeout 后重试成功，按守则仍需镜像回退 | 不同路线：build() 内真实执行 `cc --version` 探针（conf c 编译器→$CC→绝对路径→PATH 回退），首个可用者 export 到进程环境并追加到 conanautotoolchain.sh 末尾覆盖；--build/--host 三元组恒保留；conandata.yml 改有序镜像列表（gh-proxy 系在前、官方原 URL 最后，sha256 不变） |
| 10 | `make static` 报 `nids.h:14: fatal error: 'pcap.h' file not found`（2026-09-20 预检；configure 已过，HMBS_DIAG_LDFLAGS/LIBS 均含 libpcap，CFLAGS 无 -I） | src/Makefile.in 只用 `$(CFLAGS) + $(LIBS_CFLAGS)`，其中 `LIBS_CFLAGS=$(PCAP_CFLAGS)`；configure.in 回退分支（`--prefix=/` 使 `prefix/include/pcap.h` 判空）仅设 `PCAPLIB=-lpcap` 而留 `PCAP_CFLAGS` 为空；AutotoolsDeps 的 -I 进 CPPFLAGS，configure conftest 用 CPPFLAGS 能过，但 make 忽略 CPPFLAGS 故失败 | 不同路线（非 CC 探针复用）：generate() 把 `self.dependencies[libpcap].package_folder/include` 桥接进 `tc.extra_cflags -I`；build() 同路径 `export PCAP_CFLAGS=-I...`（source 之后、configure 之前）并透传给 Autotools.make；诊断增打 CPPFLAGS/PCAP_CFLAGS；conandata.yml 收敛为 CI 官方映射两项（gh-proxy + 官方原 URL，sha256 不变） |
| 11 | `make install` 报 `../mkinstalldirs: No such file or directory`（2026-09-20 预检第3轮；static 已 ar/ranlib 成功，package 阶段 `make install install_prefix` 在 build_folder 执行） | basic_layout 外置构建：src/Makefile 用 `../mkinstalldirs` 即 `<build>/mkinstalldirs`，但 configure 不复制该辅助脚本到构建树（仅源码树有）；此前只修编译未覆盖安装路径 | 不同路线（非 CFLAGS 复用）：package() 构建时把源码树 mkinstalldirs 复制到构建树（仅构建期复制，不进补丁）并 chmod 容错；`make install` 失败时回退手装三件套（libnids.a→lib、nids.h→include、libnids.3→share/man/man3，libnet/1.2 OHOS 手装先例） |
| 12 | test_package 报 `nids.h:14: fatal error: 'pcap.h' file not found`（2026-09-20 预检；主包 static 已 ar/ranlib 成功并手装，test_package CMake configure 已过、编译到 50% 失败） | 消费者侧只 `target_link_libraries(test_nids libnids::libnids)`，nids.h 公开头文件 `#include <pcap.h>` 所需的 libpcap include 经 `cpp_info.requires` 透传未落到编译行（find_package(libpcap) 虽成功但未被 link）；与前三轮 CC/工具链指纹无关 | 不同路线（不再动工具链/CC 探针）：test_package/CMakeLists.txt 显式 `target_link_libraries(test_nids libnids::libnids libpcap::libpcap)`，find_package 行保持不变；主包与 test_package conanfile 不动 |
| 13 | 上轮显式 link 后同指纹复现（2026-09-20 12:51 预检仍 `pcap.h file not found`，编译到 50% 失败） | 上轮只改 CMakeLists link 行，但 test_package/conanfile 仍只声明 tested_reference_str，libpcap 为纯透传依赖，CMakeDeps 未必落盘 Conan 版 libpcap config，target 透传链不可靠；与 CC/工具链无关 | 不同路线（不重复 link-only）：test_package/conanfile 直接 `requires libpcap/1.10.6`（与主包同版本）保证落盘 Conan config；generate 内 Python 聚合 libpcap/libnids 的 cpp_info include（存在性校验）并注入 CMAKE_C_FLAGS，与 target 链无关；CMakeLists 显式 link 保留 |

## 源码修改

无 patches/ 补丁。平台适配全部在 conanfile.py 内完成（configure 参数、config.sub 的 aarch64 兼容改写、umask 改写、mktemp shim），符合 R8（patches 禁止平台宏）与 R6（不改生成文件入仓）。

## 依赖版本

- libpcap/1.10.6（已发布，制品仓有配方）
- 无其他 Conan 依赖

## 上游测试审计

- 顶层 Makefile.in：仅 `all/static/shared/install/clean/distclean`，无 `check/test` 目标。
- src/Makefile.in：仅 `static/shared/_install/_installshared/clean`，无测试目标。
- 全包 `grep -ri "add_test\|enable_testing\|check_PROGRAMS\|TESTS =\|def test_\|TEST_F("`：0 命中。
- samples/（sniff.c/printall.c/overflows.c/nids_next.c/chksum_ctl.c）均为需 root 与真实网卡的手动示例，非自动化断言套件。
- 结论：`no_tests`，见 test_package/MANIFEST.yml 完整审计。

## 验证结果

```bash
# 待真机预检回填（conan create 真实执行）：
# - test_package test_nids 6/6 CHECK-OK
# - 上游 no_tests 标记
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libnids.a | 静态库（默认） |
| include/nids.h | 公开头文件 |
| share/man/man3/libnids.3 | 手册页 |
| licenses/COPYING | 许可证文本 |

## 注意事项

- 消费者测试避免真实抓包（无需 root）：版本宏、回调注册/注销、错误路径、结构体操作。
- 如需 `nids_killtcp` 功能，需重新评估 libnet 依赖并另行适配。
