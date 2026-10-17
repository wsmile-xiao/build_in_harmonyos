# kea-perfdhcp 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起由 Autotools 迁移；顶层 `meson.build`，`meson_version: '>=1.1.0'`）
- 编译日期: 2026-09-16（首次适配）/ 2026-09-17（补充鸿蒙特有测试用例并重跑全部门禁）
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26，aarch64-linux-ohos，libc++，C++17）
- 工作副本: `/storage/Users/currentUser/Desktop/GPQworkspace/kea-perfdhcp-3.0.3-wt`（分支 `feat/kea-perfdhcp-3.0.3`，基线 `origin/main@c8766249cd`）
- 状态: built

## 编译步骤

```bash
# 1) 语言预检（R47）：cpp / meson 工程
ohc-run.py lang-preflight kea-perfdhcp 3.0.3 --src $HOME/tmp/builds/kea-perfdhcp-3.0.3.work

# 2) Conan 生成 Meson 工具链（PkgConfigDeps + MesonToolchain）
conan install . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -of=<of>
# 3) 真实 meson setup + ninja（探索阶段，模式 B）
meson setup <builddir> <work-src> --native-file=<of>/build-release/conan/conan_meson_native.ini
ninja -C <builddir> -j6 src/bin/perfdhcp/perfdhcp src/bin/perfdhcp/tests/perfdhcp-tests

# 4) 上游测试（Meson 注册入口，实际执行）
meson test -v -C <builddir> perfdhcp-tests

# 5) 配方固化
ohc-run.py refresh-patch --auto kea-perfdhcp 3.0.3
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
ohc-run.py conan-verify kea-perfdhcp 3.0.3
ohc-run.py finish kea-perfdhcp 3.0.3 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build:17:0: ERROR: Unknown linker(s): [['llvm-ar']]`（configure 阶段，**首个错误**） | meson 对 clang 编译器默认用**裸名** `llvm-ar` 探测静态链接器（`mesonbuild/compilers/detect.py`: `defaults['clang_static_linker'] = ['llvm-ar']`），而 MesonToolchain 未写出 `ar/ranlib`；本环境/CI worker 上裸名 exec 失败（`Running 'llvm-ar --version' gave "[Errno 2] No such file or directory"`） | `generate()` 中从 `conf tools.build:compiler_executables` 的 `c` 编译器路径推导同目录 `llvm-ar`/`llvm-ranlib`，写入 `tc.binaries`（历史配方 `c-list/3.1.0` 同款先例） |
| 2 | `meson.build:186:4: ERROR: Problem encountered: Unsupported system "harmonyos".` | OHOS 上 `platform.system()` 返回 HarmonyOS，meson 据此报告 host system=`harmonyos`；Kea 用 `build_machine.system()` 做平台分支，白名单只有 linux/freebsd/netbsd/openbsd/sun/darwin | 补丁 `0001-meson.build.patch`（+6 行）：顶层把 `SYSTEM == 'harmonyos'` 归一化为 `'linux'`，一处修改使全部子目录走 Linux 分支（含 `iface_mgr_linux.cc`/`pkt_filter_lpf.cc`） |
| 3 | `meson.build:477:8: ERROR: Problem encountered: Boost TLS support broken.`（`HAVE_GENERIC_TLS_METHOD` DID NOT COMPILE；真实编译错误 `boost/core/detail/sp_thread_sleep.hpp:73: error: use of undeclared identifier 'pthread_setcancelstate'`） | OHOS musl 的 `sysroot/usr/include/pthread.h` 不声明 `pthread_setcancelstate()`（实测 grep 计数 = 0），而 boost 1.85 在 `BOOST_HAS_PTHREADS && !__ANDROID__` 时无条件调用；`boost/asio/ssl.hpp` 头链必经 | `generate()` 注入 boost 官方逃生宏 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`；复验：TLS 两个探针转为 YES |
| 4 | `Checking if "LOG4CPLUS_INITIALIZER_H" with dependency log4cplus runs: NO (127)` → `meson.build:824:24: ERROR: Unknown variable "log4cplus".` | meson 的特性探针是"编译并运行"；host 共享依赖 `liblog4cplus.so.9`（`shared=True`）不在配置期运行时 `LD_LIBRARY_PATH` 内（127 = 动态加载失败，原始输出 `Error loading shared library liblog4cplus.so.9`） | `generate()` 用 `Environment` 把各 host 依赖 `cpp_info.libdirs` 追加进 `LD_LIBRARY_PATH` 并 `save_script("conanbuildenv-kea-runtime")`（聚合进 conanbuild.sh，build 阶段自动 source） |
| 5 | 编译期 `iface_mgr_linux.cc:40: error: redefinition of 'sockaddr_storage'`（UAPI `linux/socket.h:23` 与 musl `sys/socket.h:377` 冲突） | OHOS sysroot 的 `linux/socket.h`（bionic 派生）定义 `struct sockaddr_storage`，musl `sys/socket.h` 已提供；`linux/rtnetlink.h` 间接包含前者 | 补丁 `0002-src-lib-dhcp-iface_mgr_linux.cc.patch`（+13 行）：包含 netlink 头前 `#define sockaddr_storage __linux_uapi_sockaddr_storage`，include 后 `#undef`，守卫 `__linux__ && !__GLIBC__`（libc 鉴别宏，**不使用 `__OHOS__`**，规避 R8/PF5） |

> 五处平台差异均在隔离探针中单独复现（未适配 → 报错 → 加修复 → 通过），日志见
> `reports/`（本目录同级 `logs/` 由任务侧保存），每条结论都有真实命令、原始输出与退出码。

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

## 包内容与运行期依赖

`perfdhcp` 可执行文件（`bin/perfdhcp`）+ 其 `readelf -d` NEEDED 闭包中的 10 个 Kea 共享库
（`libkea-dhcp`、`libkea-hooks`、`libkea-cc`、`libkea-asiolink`、`libkea-cryptolink`、
`libkea-dns`、`libkea-exceptions`、`libkea-util`、`libkea-log`、`libkea-log-interprocess`，
含 soname 符号链接）。上游 `INSTALL_RPATH` 指向构建机 prefix，Conan 包改用
`cpp_info.libdirs=["lib"]` 让生成的 run 环境提供 `LD_LIBRARY_PATH`。

## 鸿蒙特有测试用例（2026-09-17 补充）

本包涉及 OHOS 平台改动（2 处补丁 + 3 处工具链注入），按"涉及鸿蒙相关改动，鸿蒙特有测试用例数量≥1"
要求补充 **2 个**鸿蒙特有用例，随 `test_package` 在 `conan create` 内真实编译并执行（CMake +
`find_package(kea-perfdhcp)`）：

| 用例 | 文件 | 断言 | 覆盖内容 |
|------|------|------|----------|
| `test_ohos_platform` | `test_package/test_ohos_platform.c` | 8 | 包内 `bin/perfdhcp` 的 OHOS 平台 ABI 特征（ELFCLASS64 / `EM_AARCH64` / `ET_DYN` PIE；`DT_NEEDED` 含 musl `libc.so` 且不含 glibc `libc.so.6`；含 `libc++_shared.so`） |
| `test_ohos_runtime` | `test_package/test_ohos_runtime.c` | 6 | OHOS 加载器下的运行时闭包（DT_NEEDED 的 Kea 库全部随包分发；10 个 `libkea-*.so*` 全部 `dlopen(RTLD_NOW)` 成功；真实执行 `perfdhcp -v` 输出 `3.0.3`） |

实测结果：**2/2 通过**（`reports/conan-create.log`、`reports/test-report.md` §4）。
`test_package/conanfile.py` 由 `basic_layout` 改为 `cmake_layout`（构建 C 用例），并保留原
Python 契约测试（`test_perfdhcp.py`，11 断言）。

## R38（命令行工具）

本包产物是可执行文件（上游 `install_dir: SBINDIR`），已在软件级别目录提供
`archives/k/kea-perfdhcp/commands.json`（`type=tool`、`binary=true`）；包内可执行文件按
Conan 约定落在 `bin/`（上游 `sbindir` 经 MesonToolchain 也映射为 `bin`）。
---

**编译结束**: 2026-09-17 17:31
**最终状态**: built
