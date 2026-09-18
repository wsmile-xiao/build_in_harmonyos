# kea-hooks 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起由 Autotools 迁移；顶层 `meson.build`，`meson_version: '>=1.1.0'`）
- 编译日期: 2026-09-17（本轮核验；首次适配 2026-09-16）
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26，aarch64-linux-ohos，libc++，C++17）
- 工作副本: `/storage/Users/currentUser/Desktop/GPQworkspace/kea-hooks-3.0.3-wt`（分支 `feat/kea-hooks-3.0.3`，基线 `origin/main@c8766249cd`）
- 状态: built

## 上游目标
- 源码路径: `src/lib/hooks/`（Kea 单工程内的 hooks 框架库）
- 产物: `libkea-hooks.so.121.0.0`（SONAME `libkea-hooks.so.121`），公共头 16 个（安装到 `include/kea/hooks/`）
- 上游测试入口: `src/lib/hooks/tests/meson.build` → `test('kea-hooks-tests', kea_hooks_tests, depends: [nvl, ivl, fxl, bcl, lcl, lecl, ucl, fcl, pcl, acl], protocol: 'gtest')`

## 构建范围（与 Kea 单工程的关系）
Kea 3.0 把整棵树作为**一个** Meson 工程（顶层 `src/**/meson.build` 递归 `subdir()`，共 242 个构建目标 /
1432 个 ninja 边）。本包只拥有 `libkea-hooks`，因此配方直接驱动 Meson 并只编译本包自己的目标：

```
meson compile -C <builddir> kea-hooks kea-hooks-tests nvl ivl fxl bcl lcl lecl ucl fcl pcl acl   # 182 个 ninja 边
```

其中 `kea-hooks` 会连带构建其依赖的 kea 库（exceptions/util/util-io/log/log-interprocess/cryptolink/asiolink/cc/dns/database），
`kea-hooks-tests` 与 10 个测试夹具库（`nvl`…`acl`）是上游 `test()` 的 `depends`。
不在本包范围内的 ~1250 个目标（kea-dhcp4/kea-dhcp6 服务器、`src/lib/dhcp`、`src/lib/dhcpsrv`、YANG 模块、
其他组件的测试套件等）不构建。副作用：`src/lib/dhcp` 不参与编译，因此 OHOS `linux/socket.h` 与
musl `sys/socket.h` 的 `sockaddr_storage` 冲突（E091/E119）在本包**不出现**，补丁集只需 1 个。
`meson test` 默认会先把整个工程重建一遍，故配方中使用 `meson test --no-rebuild`。

## 编译步骤

```bash
# 1) 语言预检（R47）：cpp / meson 工程
ohc-run.py lang-preflight kea-hooks 3.0.3 --src $HOME/tmp/builds/kea-hooks-3.0.3.work

# 2) Conan 生成 Meson 工具链（PkgConfigDeps + MesonToolchain），随后真实 meson setup + 定向 ninja
conan install archives/k/kea-hooks/3.0.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -of <scratch>
. <scratch>/build-release/conan/conanbuild.sh
meson setup meson-build $HOME/tmp/builds/kea-hooks-3.0.3.work \
      --native-file <scratch>/build-release/conan/conan_meson_native.ini --prefix=/
meson compile -C meson-build kea-hooks kea-hooks-tests nvl ivl fxl bcl lcl lecl ucl fcl pcl acl

# 3) 上游测试（Meson 注册入口 + 直接执行）
meson test -v --no-rebuild -C meson-build kea-hooks-tests
./src/lib/hooks/tests/kea-hooks-tests

# 4) 配方固化
ohc-run.py refresh-patch --auto kea-hooks 3.0.3
conan create archives/k/kea-hooks/3.0.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
ohc-run.py conan-verify kea-hooks 3.0.3
ohc-run.py finish kea-hooks 3.0.3 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build:17:0: ERROR: Unknown linker(s): [['llvm-ar']]`（configure 阶段，首个错误） | meson 对 clang 编译器默认用**裸名** `llvm-ar` 探测静态链接器（`compilers/detect.py: defaults['clang_static_linker'] = ['llvm-ar']`），而 MesonToolchain 未写出 `ar/ranlib`；本环境/CI worker 上裸名 exec 失败 | `generate()` 中从 `conf tools.build:compiler_executables` 的 `c` 编译器路径推导同目录 `llvm-ar`/`llvm-ranlib`，写入 `tc.binaries`（历史配方 `c-list/3.1.0` 同款先例） |
| 2 | `meson.build:186:4: ERROR: Problem encountered: Unsupported system "harmonyos".` | OHOS 上 `platform.system()` 返回 HarmonyOS，meson 据此报告 host system=`harmonyos`；Kea 用 `build_machine.system()` 做平台分支，白名单只有 linux/freebsd/netbsd/openbsd/sun/darwin | 补丁 `0001-meson.build.patch`（+6 行）：顶层把 `SYSTEM == 'harmonyos'` 归一化为 `'linux'`，一处修改使全部子目录走 Linux 分支 |
| 3 | `meson.build:477:8: ERROR: Problem encountered: Boost TLS support broken.`（`HAVE_GENERIC_TLS_METHOD` DID NOT COMPILE；真实编译错误 `boost/core/detail/sp_thread_sleep.hpp:73: error: use of undeclared identifier 'pthread_setcancelstate'`） | OHOS musl 的 `sysroot/usr/include/pthread.h` 不声明 `pthread_setcancelstate()`（实测 grep 计数 = 0），而制品仓 boost 1.85 的 `sp_thread_sleep.hpp` 在 `BOOST_HAS_PTHREADS && !__ANDROID__ && !BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 时调用它；`boost/asio/ssl.hpp` 头链必经 | `generate()` 注入 boost 官方逃生宏 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`；复验：TLS 两个探针转为 YES |
| 4 | `Checking if "LOG4CPLUS_INITIALIZER_H" ... runs: NO (127)` → `meson.build:824:24: ERROR: Unknown variable "log4cplus".` | meson 的特性探针是“编译并运行”；host 共享依赖 `liblog4cplus.so.9`（`shared=True`）不在配置期运行时 `LD_LIBRARY_PATH` 内（127 = 动态加载失败，原始输出 `Error loading shared library liblog4cplus.so.9: (needed by .../output.exe)`） | `generate()` 用 `Environment` 把各 host 依赖 `cpp_info.libdirs` 追加进 `LD_LIBRARY_PATH` 并 `save_script("conanbuildenv-kea-runtime")`（聚合进 conanbuild.sh，build 阶段自动 source） |

> 上述 4 项均已用“去掉修复后重跑 configure”的方式复现原始错误（见 `reports/kea-hooks-3.0.3-adapt/logs/09_rootcause_repro.log`、`10_rootcause_repro2.log`），确认因果。

## 源码修改

| 补丁 | 文件 | 行数 | 内容 |
|------|------|------|------|
| 0001-meson.build.patch | `meson.build` | +6 | harmonyos → linux 平台名归一化 |

补丁不含平台宏（PF5 通过）；由 `refresh-patch --auto` 生成（R3），并已验证：把补丁应用到 pristine `.orig`
后与 `.work` 逐字节一致（sha256 `86652e0a29…`）。

## 依赖版本

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| boost | 1.85.0 | 强制 | 1.90/1.91 缺 `boost/interprocess/...`、`circular_buffer` 等 Kea 强制头 |
| log4cplus | 2.2.0.1 | 强制 | Kea 日志后端（`shared=True`，配置期运行探针需 LD_LIBRARY_PATH） |
| openssl | 3.5.8.1 | 强制 | 默认 `crypto=openssl`（CRYPTO_DEP） |
| gtest | 1.17.0.1 | test_requires | `-Dtests=enabled` |
| meson | 1.11.0 | tool_requires | Kea 需 ≥1.10（boost 无 `libboost_system`，走 header-only 模块回退） |

`conan download <dep> -r=ohpcd --only-recipe` 全部 exit_code=0；未使用本地缓存绕过、未使用 `--build=missing`。

## 验证结果（2026-09-17 复核实测）

```bash
# 上游测试（Meson 注册入口；本轮全新 builddir meson-build-r2）
meson setup meson-build-r2 <src> --native-file <conan_meson_native.ini> --prefix=/   # exit 0，OS Family: Linux
meson compile -C meson-build-r2 kea-hooks kea-hooks-tests nvl ivl fxl bcl lcl lecl ucl fcl pcl acl  # exit 0
meson test -v --no-rebuild -C meson-build-r2 kea-hooks-tests
#   1/1 kea:kea-hooks-tests OK              1.16s      Ok: 1  Fail: 0        exit_code=0
# 上游测试（直接执行）
./src/lib/hooks/tests/kea-hooks-tests
#   [==========] 121 tests from 11 test suites ran. (655 ms total)
#   [  PASSED  ] 121 tests.        exit_code=0
#   YOU HAVE 1 DISABLED TEST   (ServerHooksTest.DISABLED_OldDuplicateHooks)
# 计数口径：源码 122 个 TEST/TEST_F 宏（含 1 个 DISABLED_，gtest 不注册）；实测执行 121，通过 121，失败 0，跳过 0
# conan create（配方内 build() 已包含上游测试 + test_package）
conan create archives/k/kea-hooks/3.0.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --user=ohpcd --channel=stable
#   build(): 182 ninja 目标；1/1 kea:kea-hooks-tests OK，121 tests PASSED
#   test_package: test_kea_hooks 9/9 OK + test_ohos_platform 12/12 ok
#   conan_create_exit=0
# W3 本地 CI（finish step 5/10，JC prdiff 模式）
#   JC pass / L0 pass / L1 pass（上游测试+test_package 实证 + L1e 破坏性反向验证）/ L2 skip / L4 pass / L5 pass
#   Pass rate: 100.0% (1/1)   .ci-result.json exit_code=0
```

## 鸿蒙特有测试用例（≥1，位于 `test_package/`）

| 用例 | 文件 | 断言内容 |
|------|------|---------|
| `test_ohos_platform` | `test_package/test_ohos_platform.cpp` | ① `__OHOS__` 编译期守卫；② `package_info` 为 os=OHOS 导出的 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 确实进入消费者编译行（该 TU 内含依赖此宏才能编译的 `boost/core/detail/sp_thread_sleep.hpp`）；③ 产物 ELFCLASS64 + EM_AARCH64；④ PT_DYNAMIC/动态字符串表可读；⑤ DT_NEEDED 为 OHOS musl `libc.so` 且**非** glibc `libc.so.6`；⑥ DT_NEEDED 含 OHOS `libc++_shared.so`；⑦ OHOS loader `dlopen(RTLD_NOW)` 能解析 libkea-hooks.so 及其 kea 运行库闭包 |

实测输出（conan create / W3）见 `reports/kea-hooks-3.0.3-adapt/logs/r2_10_conan_create.log`、`r2_13_finish_r2_w3.log`。
支撑该用例的基线证据：同一 TU 若缺 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`，OHOS musl 下编译直接失败
（`boost/core/detail/sp_thread_sleep.hpp:73: error: use of undeclared identifier 'pthread_setcancelstate'`，见 `logs/r2_05_ohos_boost_probe.log`）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `lib/libkea-hooks.so.121.0.0` | 262 KiB | hooks 框架库（SONAME `libkea-hooks.so.121`）+ soname 符号链接；直接 DT_NEEDED = `libkea-cc.so.83`、`libkea-log.so.75`、`libkea-util.so.102`、`libkea-exceptions.so.45`、`libc++_shared.so`、`libc.so` |
| `lib/libkea-*.so*` | — | 其余 3 个 Kea 运行期库构成完整加载闭包：`libkea-asiolink.so.88`、`libkea-cryptolink.so.64`、`libkea-log-interprocess.so.3`（`readelf -d` 递归实测，非 meson `link_with` 列表） |
| `include/kea/hooks/*.h` | — | 16 个公共头（与上游 `install_headers(..., subdir: 'kea/hooks')` 一致） |
| `include/kea/{cc,log,log/interprocess,util,exceptions,asiolink,cryptolink}/*.h` | — | 闭包库的公共头（被 hooks 头直接 include，缺则消费者无法编译） |
| `licenses/COPYING` | — | MPL-2.0 |

## 注意事项

- 公共头的 include 根是 `<prefix>/include/kea`（上游即如此安装：`install_headers(..., subdir: 'kea/hooks')`），
  消费方按 `#include <hooks/hooks.h>` 使用；conan 包通过 `cpp_info.includedirs = ["include/kea"]` 暴露。
- Kea 尚未单独打包，因此 `libkea-hooks.so` 的加载闭包（直接 4 个 + 传递合计 7 个 kea 库）随本包一起交付，安装后即可直接加载（`test_ohos_platform` 的 `dlopen(RTLD_NOW)` 已实证）。
- `libkea-hooks.so` 的 RUNPATH 含构建期路径（上游 meson 的 build_rpath），消费方加载时以自身 RPATH /
  `LD_LIBRARY_PATH` 为准（Conan 的 `VirtualRunEnv` 已覆盖）。
- 上游 Kea 全量测试套件包含需要特权/网络的用例，本配方只跑覆盖本库的 `kea-hooks-tests`（`upstream_test_suites`）。
- 本包不产出命令行工具，R38 不适用（无需 `commands.json`）。
- W3 本地 CI 的 JC 门禁在**整仓全量模式**下会被 main 存量垃圾文件（`archives/c/cloog/0.21.1/.build-closed`、
  `.staging-verified`，由 cloog 0.21.1 的 PR 带入 main）误伤；CI 正式路径使用 `pr.diff`（prdiff 模式），
  本包 14 个 PR 文件在该模式下 JC 全通过。详见适配报告 §W3。
---

**编译结束**: 2026-09-17 17:53
**最终状态**: built
