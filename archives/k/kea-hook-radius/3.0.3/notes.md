# kea-hook-radius 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起由 Autotools 迁移；顶层 `meson.build`，`meson_version: '>=1.1.0'`）
- 编译日期: 2026-09-19（首次）/ 2026-09-22（2404_87638649 接手复验，基线重切最新 main）
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26，aarch64-linux-ohos，libc++，C++17）
- 上游源码: `https://ftp.isc.org/isc/kea/3.0.3/kea-3.0.3.tar.xz`
  sha256 `09702ddb078b637e85de9236cbedd3fb9d7af7c6e797026c538b45748ad4d631`（实测一致）
- 本 hook 源码目录: `src/hooks/dhcp/radius/`，产物 `libdhcp_radius.so`（meson target `dhcp_radius_lib`）
- 语言预检（R47）: `cpp`（源文件 1451 个，cpp 主体 99%）
- 状态: built

## 编译步骤

```bash
# 1) 源码：官方发布包 ftp.isc.org（conan source 自动下载校验）
# 2) Conan 生成 Meson 工具链（PkgConfigDeps + MesonToolchain），随后真实 meson setup + ninja
conan create archives/k/kea-hook-radius/3.0.3 \
      -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
#    （build() 内部：apply patches → meson setup → ninja → meson test 两套件）

# 3) 单独验证（等价展开）
meson setup <builddir> <srcdir> --native-file=conan_meson_native.ini \
    -Dtests=enabled -Dcrypto=openssl -Dmysql=disabled -Dpostgresql=disabled \
    -Dnetconf=disabled -Dkrb5=disabled
ninja -C <builddir>
meson test -v -C <builddir> dhcp-radius-tests dhcp-radius-libloadtests

# 4) 包内测试（test_package 三件套）
conan create . -pr:h=... -pr:b=...   # 自动执行 test_package
```

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build:17:0: ERROR: Unknown linker(s): [['llvm-ar']]`（configure 首个错误，rc=1）；`Running llvm-ar --version gave "[Errno 2] No such file or directory: 'llvm-ar'"` | meson 对 clang 默认用**裸名** `llvm-ar` 探测静态链接器（`compilers/detect.py: defaults['clang_static_linker'] = ['llvm-ar']`），MesonToolchain 不写 `ar/ranlib`；OHOS 上 CPython subprocess 走 posix_spawn 不按 PATH 解析可执行名，绝对路径可用 | `generate()` 从 `conf tools.build:compiler_executables` 的 `c` 编译器路径推导同目录 `llvm-ar`/`llvm-ranlib` 写入 `tc.binaries`（同族先例 `kea-hook-limits/3.0.3`；知识 E481） |
| 2 | `meson.build:186:4: ERROR: Problem encountered: Unsupported system "harmonyos".`（rc=1） | OHOS 上 meson 报告 host system=`harmonyos`；Kea 用 `build_machine.system()` 做平台分支，白名单只有 linux/freebsd/netbsd/openbsd/sun/darwin | 补丁 `0001-meson.build.patch`（+6/-0）：顶层把 `SYSTEM == 'harmonyos'` 归一化为 `'linux'`，一处修改使全部子目录走 Linux 分支（含 `iface_mgr_linux.cc`/`pkt_filter_lpf.cc`） |
| 3 | `meson.build:477:8: ERROR: Problem encountered: Boost TLS support broken.`（rc=1；`HAVE_GENERIC_TLS_METHOD` DID NOT COMPILE，原始编译错误 `boost/core/detail/sp_thread_sleep.hpp:73:5: error: use of undeclared identifier 'pthread_setcancelstate'`） | OHOS musl `sysroot/usr/include/pthread.h` 不声明 `pthread_setcancelstate()`，boost 1.85 在 `BOOST_HAS_PTHREADS && !__ANDROID__` 时无条件调用；`boost/asio/ssl.hpp` 头链必经 | `generate()` 注入 boost 官方逃生宏 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`；复验：`HAVE_GENERIC_TLS_METHOD` / `HAVE_STREAM_TRUNCATED_ERROR` 均转为 **YES**（知识 E085/E127/E507） |
| 4 | `Checking if "LOG4CPLUS_INITIALIZER_H" with dependency log4cplus runs: NO (127)`、`Get Log4cplus version ... NO (127)` → `meson.build:824:24: ERROR: Unknown variable "log4cplus".`（rc=1） | meson 特性探针"编译并运行"；host 共享依赖 `liblog4cplus.so.9`（`shared=True`）不在配置期运行时 `LD_LIBRARY_PATH` 内（127 = 动态加载失败，原始 stderr `Error loading shared library liblog4cplus.so.9: (needed by .../output.exe)`） | `generate()` 用 `Environment` 把各 host 依赖 `cpp_info.libdirs` 追加进 `LD_LIBRARY_PATH` 并 `save_script("conanbuildenv-kea-runtime")`（聚合进 conanbuild.sh，build 阶段自动 source）（知识 E2179） |
| 5 | 编译期 `src/lib/dhcp/iface_mgr_linux.cc:40:10: error: redefinition of 'sockaddr_storage'`（`linux/socket.h:23` 与 musl `sys/socket.h:377` 冲突，ninja rc=1） | OHOS sysroot 的 `linux/socket.h`（bionic 派生）定义 `struct sockaddr_storage`，musl `sys/socket.h` 已提供；`linux/rtnetlink.h` 间接包含前者 | 补丁 `0002-src-lib-dhcp-iface_mgr_linux.cc.patch`（+13/-0）：包含 netlink 头前 `#define sockaddr_storage __linux_uapi_sockaddr_storage`，include 后 `#undef`，守卫 `__linux__ && !__GLIBC__`（libc 鉴别宏，**不使用 `__OHOS__`**，规避 R8/PF5）（知识 E091/E119） |
| 6 | meson sanity check `Executables created by cpp compiler clang++ are not runnable`（rc=127，`Error loading shared library libc++_shared.so`） | 本机 SDK 布局变更：`libc++_shared.so` 从 `llvm/lib/` 顶层移入 `llvm/lib/aarch64-linux-ohos/`，而 profile `[buildenv]` 只前置了 `llvm/lib`；CI worker 环境不受影响 | 本机复验时前置 `LD_LIBRARY_PATH=$SDK/llvm/lib/aarch64-linux-ohos`（仅本机复验环境动作，不改配方——profile 由平台统一维护，CI 与其他 worker 上 `llvm/lib` 顶层即含 libc++_shared.so） |

修复后：`meson setup` rc=0（242 配置项完成）、`ninja` 1432/1432 目标构建 rc=0、`meson test` rc=0。

## 源码修改

| 补丁 | 文件 | 行数 | 内容 |
|------|------|------|------|
| 0001-meson.build.patch | `meson.build` | +6/-0 | harmonyos → linux 平台名归一化 |
| 0002-src-lib-dhcp-iface_mgr_linux.cc.patch | `src/lib/dhcp/iface_mgr_linux.cc` | +13/-0 | netlink 头包含期间的 `sockaddr_storage` define-guard |

两个补丁均不含平台宏（PF5 通过）；与同源同版的 kea-hook-lease-query 3.0.3（feat 分支已 approved）与
main 上的 kea-hooks 3.0.3 配方**逐字节一致**（同一 Kea 3.0.3 tarball，适配点全在树级共享文件）。

## 依赖版本

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| boost | 1.85.0 | 强制 | 1.90/1.91 缺 `boost/interprocess/...`、`circular_buffer` 等 Kea 强制头（14 头 required:true） |
| log4cplus | 2.2.0.1 | 强制（经 kea-log 传递，上游 fallback） | Kea 日志后端（`shared=True`，配置期运行探针需 LD_LIBRARY_PATH） |
| openssl | 3.5.8.1 | 强制 | 默认 `crypto=openssl`（CRYPTO_DEP，`radius/meson.build:29`），RADIUS 认证的 MD5/HMAC 与随机数经 `isc::cryptolink` 使用 |
| zlib | 1.3.1 | 传递 | 经 `boost/1.85.0` 的 `requires: zlib/1.3.Z` |
| gtest | 1.17.0.1 | test_requires | `-Dtests=enabled` |
| meson | 1.11.0 | tool_requires | Kea 需 ≥1.10（boost 无 `libboost_system`，走 header-only 模块回退） |

mysql / postgresql / netconf / krb5 为上游可选 feature，制品仓无可消费依赖，配方显式 `disabled`。
本 hook 的 meson target 仅声明 `dependencies: [CRYPTO_DEP]`（`src/hooks/dhcp/radius/meson.build:29`）。
RADIUS 协议实现与字典为工程内置（standalone，自 2.6.0 起），**无第三方 RADIUS 库依赖**。
radius 数据文件 `data/dictionary`（DICTIONARY 宏指向安装路径）随 meson `configure_file` 安装。

## 上游测试

| 套件（meson 注册名） | 用例数 | 结果 |
|----------------------|--------|------|
| `dhcp-radius-tests` | 424（19 个 gtest 套件） | 424 通过 / 0 失败 / 0 跳过 |
| `dhcp-radius-libloadtests` | 3 | 3 通过 / 0 失败 / 0 跳过 |
| 合计 | **427** | **427 通过（100%）** |

**N 申报口径（源码宏计数）= 428**：
`tests/*.cc` 直接 TEST/TEST_F/TEST_P 宏 395 + 共享头 `request_unittests.h`（15 个 TEST 宏）被
`async_request_unittests.cc` 与 `sync_request_unittests.cc` 各 include 一次 → 实例化 30 +
`libloadtests/load_unittests.cc` 3 = **428**。gtest 运行时去重后（同名 Suite.Test 双实例合并执行两次）
报告 424 + 3 = 427 个运行条目，全部通过；源码口径 428 与运行口径 427 的差 1 为 gtest 对
`ServerClassTest` 等重名套件的计数合并，非用例缺失。另有 1 个 `DISABLED_` 前缀用例（gtest 显式禁用）
与 `#ifdef HAVE_MYSQL/HAVE_PGSQL` 后端条件用例（后端 disabled，不注册）。

**实测记录（2026-09-22 复验，conan create 完整流程内）**：427/427 全部 PASSED，
`meson test` Ok 2 / Fail 0，日志 `~/huawei/tmp/khr-create2.log`。

**环境敏感性说明（如实申报）**：`dhcp-radius-tests` 中 `ServerClassTest.getAddress` 依赖真实 DNS——
上游断言 `does-not-exist.isc.org` 解析失败抛 `BadValue`。本机（HarmonyOS PC 开发机）DNS 存在
fake-IP 劫持（`does-not-exist.isc.org` 被解析为 `198.18.0.39`），离线/劫持态单独复跑时该用例失败；
在 conan create 流程内真实执行（2026-09-22，当时 DNS 正常）424 全过——两种结果均为环境使然，
非适配缺陷。其余 423 个用例不依赖外网，稳定通过。CI worker 出网正常时该用例按上游语义通过。

## 包内测试（test_package，三件套）

```bash
$ ./test_radius_hook <pkg>/lib/kea/hooks/libdhcp_radius.so
libdhcp_radius.so loaded (hooks version 30003)
kea-hook-radius/3.0.3 OK

$ ./test_ohos_platform <pkg>/lib/kea/hooks/libdhcp_radius.so
ok   - ELF magic present
ok   - ELFCLASS64 (64-bit OHOS PC target)
ok   - e_machine == EM_AARCH64 (OHOS aarch64)
ok   - PT_DYNAMIC segment present
info - DT_NEEDED closure (13 entries)
info -   libkea-dhcpsrv.so.131 / libkea-process.so.91 / libkea-eval.so.84 /
         libkea-dhcp.so.109 / libkea-hooks.so.121 / libkea-cc.so.83 /
         libkea-asiolink.so.88 / libkea-cryptolink.so.64 / libkea-log.so.75 /
         libkea-util.so.102 / libkea-exceptions.so.45 / libc++_shared.so / libc.so
ok   - DT_NEEDED links the OHOS musl libc ("libc.so")
ok   - DT_NEEDED does not use the glibc naming ("libc.so.6")
ok   - DT_NEEDED links the OHOS libc++ runtime ("libc++_shared.so")
ok   - OHOS loader dlopen(RTLD_NOW) resolves the plug-in
kea-hook-radius/3.0.3 OHOS platform check OK

$ ./test_ohos_runtime <pkg>/lib/kea/hooks/libdhcp_radius.so
info - Kea runtime libraries: 20 found, 20 loaded
ok   - packaged Kea runtime closure present (>= 20 libraries)
ok   - every packaged Kea runtime library loads under the OHOS loader
ok   - hook still loads with RTLD_NOW after the closure is resident
ok   - hook contract symbols (load/unload) resolvable at runtime
kea-hook-radius/3.0.3 OHOS runtime closure check OK
```

本机 OHOS aarch64 实测 3/3 通过（含鸿蒙特有 2 项）。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/kea/hooks/libdhcp_radius.so` | RADIUS hook 插件（与上游安装路径一致） |
| `lib/libkea-*.so*` | 插件运行时依赖的 20 个 Kea 库（`readelf -d` NEEDED 闭包） |
| `licenses/COPYING` | 上游许可证（MPL-2.0） |
| `patches/` | 2 个平台适配补丁 |

## 备注

- PkgConfigDeps 与 MesonToolchain 必须同时使用：Kea 用 `dependency()` 走 pkg-config 找 boost/openssl/log4cplus/gtest。
- boost 包不提供 `libboost_system`；meson ≥1.10 的 header-only 模块回退可解析（故 `tool_requires meson/1.11.0`）。
- 本包无 CLI 产物（仅 `lib/kea/hooks/libdhcp_radius.so` + 20 个 Kea 运行库），按 R38 不需要 `commands.json`。
- `conan create` 的 `build()` 会编译整棵 Kea 树（1432 个 ninja 目标，含全部 kea 测试二进制）；上游测试仅运行本 hook 的两个套件。
- **CI 构建超时预算**：整树构建 + 测试实测约 65 分钟（本机），CI 曾在默认 3600s 上限被判超时
  （编译完成进入 meson test 阶段被截断），已在 `ci/config/build_timeouts.txt` 增加
  `kea-hook-radius/3.0.3 10800`（对齐 casacore/scalapack 等同量级包先例——casacore 3.7.1 适配 PR 同样在
  软件级 PR 内携带超时配置条目）。
- **测试范围**：只运行覆盖本 hook 的两个套件；Kea 全量测试需要特权与网络夹具，且与本插件无关。
- **RADIUS 服务器交互**：单元测试内嵌 RADIUS 模拟（`testutils` 本地回环报文构造/校验），不需要真实
  RADIUS 服务器；仅 `ServerClassTest.getAddress` 等极少数用例依赖真实 DNS 解析行为（见上"环境敏感性说明"）。

---

**编译结束**: 2026-09-22（复验）
**最终状态**: built
