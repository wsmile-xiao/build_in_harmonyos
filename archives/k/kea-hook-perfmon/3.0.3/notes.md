# kea-hook-perfmon 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起由 Autotools 迁移；顶层 `meson.build`，`meson_version: '>=1.1.0'`）
- 编译日期: 2026-09-16
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26，aarch64-linux-ohos，libc++，C++17）
- 工作副本: `/storage/Users/currentUser/Desktop/GPQworkspace/kea-hook-perfmon-3.0.3-wt`（分支 `feat/kea-hook-perfmon-3.0.3`，基线 `origin/main@b23a821309`）
- 状态: built

## 编译步骤

```bash
# 1) 语言预检（R47）：cpp / meson 工程
ohc-run.py lang-preflight kea-hook-perfmon 3.0.3 --src $HOME/tmp/builds/kea-hook-perfmon-3.0.3.work

# 2) Conan 生成 Meson 工具链（PkgConfigDeps + MesonToolchain），随后真实 meson setup + ninja
meson setup <builddir> <srcdir> --native-file=<out>/conan_meson_native.ini -Dtests=enabled
ninja -C <builddir> -j6 src/hooks/dhcp/perfmon/libdhcp_perfmon.so \
      src/hooks/dhcp/perfmon/tests/dhcp-perfmon-lib-tests \
      src/hooks/dhcp/perfmon/libloadtests/dhcp-perfmon-libload-tests

# 3) 上游测试（Meson 注册入口，实际执行）
meson test -v -C <builddir> dhcp-perfmon-lib-tests dhcp-perfmon-libload-tests

# 4) 配方固化
ohc-run.py refresh-patch --auto kea-hook-perfmon 3.0.3
ohc-run.py conan-init kea-hook-perfmon 3.0.3     # 生成模板后按 meson 工程手工改写
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
ohc-run.py conan-verify kea-hook-perfmon 3.0.3
ohc-run.py finish kea-hook-perfmon 3.0.3 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build:17:0: ERROR: Unknown linker(s): [['llvm-ar']]`（configure 阶段，首个错误） | meson 对 clang 编译器默认用**裸名** `llvm-ar` 探测静态链接器（`compilers/detect.py: defaults['clang_static_linker'] = ['llvm-ar']`），而 MesonToolchain 未写出 `ar/ranlib`；本环境/CI worker 上裸名 exec 失败（实测 `subprocess.run(['llvm-ar','--version'])` → FileNotFoundError，绝对路径 rc=0） | `generate()` 中从 `conf tools.build:compiler_executables` 的 `c` 编译器路径推导同目录 `llvm-ar`/`llvm-ranlib`，写入 `tc.binaries`（历史配方 `c-list/3.1.0` 同款先例） |
| 2 | `meson.build:186:4: ERROR: Problem encountered: Unsupported system "harmonyos".` | OHOS 上 `platform.system()` 返回 HarmonyOS，meson 据此报告 host system=`harmonyos`；Kea 用 `build_machine.system()` 做平台分支，白名单只有 linux/freebsd/netbsd/openbsd/sun/darwin | 补丁 `0001-meson.build.patch`（+6 行）：顶层把 `SYSTEM == 'harmonyos'` 归一化为 `'linux'`，一处修改使全部子目录走 Linux 分支（含 `iface_mgr_linux.cc`/`pkt_filter_lpf.cc`） |
| 3 | `meson.build:477:8: ERROR: Problem encountered: Boost TLS support broken.`（`HAVE_GENERIC_TLS_METHOD` DID NOT COMPILE；真实编译错误 `boost/core/detail/sp_thread_sleep.hpp:73: error: use of undeclared identifier 'pthread_setcancelstate'`） | OHOS musl 的 `sysroot/usr/include/pthread.h` 不声明 `pthread_setcancelstate()`（实测 grep 计数 = 0），而 boost 1.85 在 `BOOST_HAS_PTHREADS && !__ANDROID__` 时无条件调用；`boost/asio/ssl.hpp` 头链必经 | `generate()` 注入 boost 官方逃生宏 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`；复验：TLS 两个探针转为 YES |
| 4 | `Checking if "LOG4CPLUS_INITIALIZER_H" ... runs: NO (127)` → `meson.build:824:24: ERROR: Unknown variable "log4cplus".` | meson 的特性探针是“编译并运行”；host 共享依赖 `liblog4cplus.so.9`（`shared=True`）不在配置期运行时 `LD_LIBRARY_PATH` 内（127 = 动态加载失败，原始输出 `Error loading shared library liblog4cplus.so.9`） | `generate()` 用 `Environment` 把各 host 依赖 `cpp_info.libdirs` 追加进 `LD_LIBRARY_PATH` 并 `save_script("conanbuildenv-kea-runtime")`（聚合进 conanbuild.sh，build 阶段自动 source） |
| 5 | 编译期 `iface_mgr_linux.cc:40: error: redefinition of 'sockaddr_storage'`（UAPI `linux/socket.h:23` 与 musl `sys/socket.h:377` 冲突） | OHOS sysroot 的 `linux/socket.h`（bionic 派生）定义 `struct sockaddr_storage`，musl `sys/socket.h` 已提供；`linux/rtnetlink.h` 间接包含前者 | 补丁 `0002-src-lib-dhcp-iface_mgr_linux.cc.patch`（+13 行）：包含 netlink 头前 `#define sockaddr_storage __linux_uapi_sockaddr_storage`，include 后 `#undef`，守卫 `__linux__ && !__GLIBC__`（libc 鉴别宏，**不使用 `__OHOS__`**，规避 R8/PF5） |

## 源码修改

| 补丁 | 文件 | 行数 | 内容 |
|------|------|------|------|
| 0001-meson.build.patch | `meson.build` | +6 | harmonyos → linux 平台名归一化 |
| 0002-src-lib-dhcp-iface_mgr_linux.cc.patch | `src/lib/dhcp/iface_mgr_linux.cc` | +13 | netlink 头包含期间的 `sockaddr_storage` define-guard |

两处补丁均不含平台宏（PF5 通过）；补丁由 `refresh-patch --auto` 生成（R3）。

## 依赖版本

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| boost | 1.85.0 | 强制 | 1.90/1.91 缺 `boost/interprocess/...`、`circular_buffer` 等 Kea 强制头 |
| log4cplus | 2.2.0.1 | 强制 | Kea 日志后端（`shared=True`，配置期运行探针需 LD_LIBRARY_PATH） |
| openssl | 3.5.8.1 | 强制 | 默认 `crypto=openssl`（CRYPTO_DEP） |
| gtest | 1.17.0.1 | test_requires | `-Dtests=enabled` |
| meson | 1.11.0 | tool_requires | Kea 需 ≥1.10（boost 无 `libboost_system`，走 header-only 模块回退） |

`conan download <dep> -r=ohpcd --only-recipe` 全部 exit_code=0；未使用本地缓存绕过、未使用 `--build=missing`。

## 验证结果

```bash
# 构建
ninja -C build-r5 -j6 <perfmon hook + 2 test targets>     # exit_code=0（263/263）
# 上游测试（Meson 注册入口）
meson test -v -C build-r5 dhcp-perfmon-lib-tests dhcp-perfmon-libload-tests
#   1/2 dhcp-perfmon-libload-tests   OK
#   2/2 dhcp-perfmon-lib-tests       OK
# 直接执行
./dhcp-perfmon-lib-tests          → [==========] 125 tests from 18 test suites ran. / [  PASSED  ] 125 tests.  exit_code=0
./dhcp-perfmon-libload-tests      → [==========] 5 tests from 1 test suite ran.   / [  PASSED  ] 5 tests.    exit_code=0
# 计数口径：t/s 126 个 TEST/TEST_F 宏（含 1 个 DISABLED_speed，gtest 不注册）+ libloadtests 5 = 131 宏；实测执行 130，通过 130，失败 0，跳过 0

# 包内测试（test_package，2 项：消费者契约 + 鸿蒙特有）
$ conan test test_package kea-hook-perfmon/3.0.3 -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>
# (1) 消费者契约
$ ./test_perfmon_hook <pkg>/lib/kea/hooks/libdhcp_perfmon.so
libdhcp_perfmon.so loaded (hooks version 30003)
kea-hook-perfmon/3.0.3 OK
# (2) 鸿蒙特有平台校验
$ ./test_ohos_platform <pkg>/lib/kea/hooks/libdhcp_perfmon.so
ok   - ELF magic present
ok   - ELFCLASS64 (64-bit OHOS PC target)
ok   - e_machine == EM_AARCH64 (OHOS aarch64)
ok   - PT_DYNAMIC segment present
ok   - DT_NEEDED links the OHOS musl libc ("libc.so")
ok   - DT_NEEDED does not use the glibc naming ("libc.so.6")
ok   - DT_NEEDED links the OHOS libc++ runtime ("libc++_shared.so")
ok   - OHOS loader dlopen(RTLD_NOW) resolves the plug-in
kea-hook-perfmon/3.0.3 OHOS platform check OK
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `lib/kea/hooks/libdhcp_perfmon.so` | 551 KB | perfmon hook 插件（SONAME `libdhcp_perfmon.so`） |
| `lib/libkea-*.so*` | — | 20 个 Kea 运行期库（`readelf -d` NEEDED 闭包）+ soname 符号链接 |
| `licenses/COPYING` | — | MPL-2.0 |

## 注意事项

- 插件由 Kea 服务器 `dlopen()` 加载，**不是**被链接的库：包内 `cpp_info.libs` 为空，仅保留 `libdirs` 供运行期环境使用。
- 上游 Kea 全量测试套件包含需要特权/网络的用例，本配方只跑覆盖本插件的两个套件（`upstream_test_suites`）。
- 本包不产出命令行工具，R38 不适用（无需 `commands.json`）。
- **鸿蒙特有测试 1 项**（`test_package/test_ohos_platform.c`）：上游两个 gtest 套件只验证 hook 逻辑，
  不校验产物平台 ABI；该用例补充校验 OHOS aarch64/musl/libc++ 平台签名（EM_AARCH64、
  DT_NEEDED 为 `libc.so` 而非 glibc 的 `libc.so.6`、`libc++_shared.so`）与 OHOS 加载器可解析性。
---

**编译结束**: 2026-09-17 09:03
**最终状态**: built
