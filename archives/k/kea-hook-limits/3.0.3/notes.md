# kea-hook-limits 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起由 Autotools 迁移；无 configure.ac）
- 编译日期: 2026-09-16
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，sysroot musl + libc++）
- 目标平台: OHOS / HarmonyOS PC aarch64（profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built

## 编译步骤

1. `conan install . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>`（PkgConfigDeps + MesonToolchain）
2. `meson setup <builddir> <srcdir> --native-file=conan_meson_native.ini -Dtests=enabled`
   —— 配置期 242 个构建目标；探针 `HAVE_GENERIC_TLS_METHOD` / `LOG4CPLUS_INITIALIZER_H` 均为 YES
3. `ninja -j6 src/hooks/dhcp/limits/libdhcp_limits.so \
        src/hooks/dhcp/limits/tests/dhcp-limits-tests \
        src/hooks/dhcp/limits/libloadtests/dhcp-limits-libload-tests`（255 目标，0 错误）
4. `meson test -v dhcp-limits-tests dhcp-limits-libloadtests` → 2/2 OK

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build:17:0: ERROR: Unknown linker(s): [['llvm-ar']]` / `Running llvm-ar --version gave [Errno 2]` | 宿主环境 `AR=llvm-ar`（裸名）被 mesh 静态链接器探测采用；OHOS 上 CPython subprocess 经 posix_spawn 执行**不解析 PATH**，裸名直接 ENOENT（`which llvm-ar` 却能找到） | `generate()` 从 `tools.build:compiler_executables` 的编译器目录推导 `llvm-ar`/`llvm-ranlib` **绝对路径**写入 machine file `[binaries]` |
| 2 | `meson.build:186:4: ERROR: Problem encountered: Unsupported system "harmonyos".` | OHOS 上 meson 的 `build_machine.system()` 返回 `harmonyos`；Kea 白名单只含 linux/bsd/solaris/darwin | 补丁 `0001-meson.build.patch`：`SYSTEM == 'harmonyos'` 归一化为 `'linux'`（一处修改使 `src/lib/dhcp` 等所有子目录走 Linux 分支） |
| 3 | `meson.build:477:8: ERROR: Problem encountered: Boost TLS support broken.`（首错 `boost/core/detail/sp_thread_sleep.hpp:73: use of undeclared identifier 'pthread_setcancelstate'`） | OHOS musl 的 `<pthread.h>` 不声明 `pthread_setcancelstate()`（实测 grep 计数 0），boost 1.85 的 `sp_thread_sleep.hpp` 无条件调用 | `tc.extra_cxxflags` 注入 boost 官方逃生宏 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE` |
| 4 | `LOG4CPLUS_INITIALIZER_H ... runs: NO (127)` + `meson.build:824:24: ERROR: Unknown variable "log4cplus"` | meson 的“编译并运行”探针在 native 构建下真实执行；探针链接的 `liblog4cplus.so.9` 不在配置期 `LD_LIBRARY_PATH`（127 = 动态加载失败，实测复现 `Error loading shared library liblog4cplus.so.9`） | `generate()` 用 `Environment` 把各 host 依赖 `cpp_info.libdirs` 追加进 `LD_LIBRARY_PATH`，`save_script("conanbuildenv-kea-runtime")` 聚合进 `conanbuild.sh` |
| 5 | `ninja FAILED: src/lib/dhcp/libkea-dhcp.so.109.0.0.p/iface_mgr_linux.cc.o` → `.../sysroot/usr/include/linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'` | OHOS sysroot 的 bionic 派生 `linux/socket.h` 与 musl `sys/socket.h:377` 都定义 `struct sockaddr_storage`；`linux/rtnetlink.h` 间接包含前者 | 补丁 `0002-src-lib-dhcp-iface_mgr_linux.cc.patch`：包含 netlink 头前后 `#define sockaddr_storage __linux_uapi_sockaddr_storage` / `#undef`，守卫用 `__linux__ && !__GLIBC__`（标准 libc 鉴别宏，**不含平台宏**） |

## 源码修改

| 补丁 | 文件 | 改动 | 内容 |
|------|------|------|------|
| `0001-meson.build.patch` | `meson.build` | +6 行 | `SYSTEM == 'harmonyos'` → `'linux'` 归一化 |
| `0002-src-lib-dhcp-iface_mgr_linux.cc.patch` | `src/lib/dhcp/iface_mgr_linux.cc` | +13 行 | netlink 头包含期间重命名 UAPI `sockaddr_storage` |

两处平台差异均在 `refresh-patch --auto` 追踪模式下生成（`orig 8d767831f5173e40` → `work ade2138099f6821c`，与 manifest.yaml `patch_generation` 一致）。

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| boost | 1.85.0 | requires（**必须固定**：1.90 缺 `interprocess_upgradable_mutex.hpp`，1.91 缺 `circular_buffer.hpp`，均为 Kea meson.build 的 required 头） |
| log4cplus | 2.2.0.1 | requires |
| openssl | 3.5.8.1 | requires（默认 crypto 后端） |
| zlib | 1.3.1 | boost 传递依赖 |
| gtest | 1.17.0.1 | test_requires（`-Dtests=enabled` 时） |
| meson | 1.11.0 | tool_requires（须 ≥ 1.10：boost 包无 libboost_system，依赖 meson 的 header-only 模块回退） |

## 验证结果

```bash
# 上游测试（真实执行）
$ meson test -v -C <builddir> dhcp-limits-tests dhcp-limits-libloadtests
1/2 kea:dhcp-limits-libloadtests OK   0.36s
2/2 kea:dhcp-limits-tests        OK   8.40s
Ok: 2   Fail: 0
exit_code=0

# 直接执行（逐用例）
$ ./dhcp-limits-tests        → 192 tests from 5 test suites ran. [ PASSED ] 192 tests. 0 failed, 0 skipped
$ ./dhcp-limits-libload-tests → 15 tests from 1 test suite ran.  [ PASSED ]  15 tests. 0 failed, 0 skipped

# 包内测试（test_package，3 项：1 消费者契约 + 2 鸿蒙特有）
$ conan test test_package kea-hook-limits/3.0.3 -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>
# (1) 消费者契约
$ ./test_limits_hook <pkg>/lib/kea/hooks/libdhcp_limits.so
libdhcp_limits.so loaded (hooks version 30003)
kea-hook-limits/3.0.3 OK
# (2) 鸿蒙特有 #1：平台 ABI 签名
$ ./test_ohos_platform <pkg>/lib/kea/hooks/libdhcp_limits.so
ok   - ELF magic present
ok   - ELFCLASS64 (64-bit OHOS PC target)
ok   - e_machine == EM_AARCH64 (OHOS aarch64)
ok   - PT_DYNAMIC segment present
ok   - DT_NEEDED links the OHOS musl libc ("libc.so")
ok   - DT_NEEDED does not use the glibc naming ("libc.so.6")
ok   - DT_NEEDED links the OHOS libc++ runtime ("libc++_shared.so")
ok   - OHOS loader dlopen(RTLD_NOW) resolves the plug-in
kea-hook-limits/3.0.3 OHOS platform check OK
# (3) 鸿蒙特有 #2：OHOS 加载器解析完整运行时闭包
$ ./test_ohos_runtime <pkg>/lib/kea/hooks/libdhcp_limits.so
ok   - OHOS loader dlopen(RTLD_NOW): libkea-exceptions.so.45.0.0
ok   - OHOS loader dlopen(RTLD_NOW): libkea-dhcpsrv.so.131.0.0    （共 20 个，逐个成功）
ok   - packaged Kea runtime closure present (>= 20 libraries)
ok   - every packaged Kea runtime library loads under the OHOS loader
info - Kea runtime libraries: 20 found, 20 loaded
ok   - hook still loads with RTLD_NOW after the closure is resident
ok   - hook contract symbols (load/unload) resolvable at runtime
kea-hook-limits/3.0.3 OHOS runtime closure check OK
exit_code=0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `lib/kea/hooks/libdhcp_limits.so` | 281 KB | limits hook 插件 |
| `lib/libkea-*.so*` | ~22 MB | 20 个 Kea 运行时库（NEEDED 闭包，含 soname 符号链接） |

## 注意事项

- 本 hook 不是被链接的库，而是由 Kea 服务器 `dlopen()` 加载；`cpp_info.libs`/`includedirs` 故意为空，
  仅保留 `libdirs` 以便消费者的运行期环境指向包内 Kea 库。
- 可选后端（mysql/postgresql/netconf/krb5）在配方中显式 `disabled`，避免依赖宿主机探测（制品仓亦未提供对应依赖）。
- 只运行本 hook 的两个测试套件：Kea 全量测试套件需要特权与网络夹具，与本 hook 无关。
- `llvm-ar` 绝对路径注入（问题 1）是 OHOS 平台通用坑，非本库特有；同批 Kea hook 共用同一处理。
- **鸿蒙特有测试 2 项**（`test_package/test_ohos_platform.c`、`test_package/test_ohos_runtime.c`）：上游两个 gtest 套件只验证 hook 逻辑，
  不校验产物平台 ABI 与加载器行为；这两项分别补充校验 OHOS aarch64/musl/libc++ 平台签名（EM_AARCH64、
  DT_NEEDED 为 `libc.so` 而非 glibc 的 `libc.so.6`、`libc++_shared.so`）与 OHOS 加载器对 20 个 Kea 运行时库
  完整 NEEDED 闭包的运行期可解析性。实测 2/2 通过。
---

**编译结束**: 2026-09-16 19:26
**最终状态**: built
