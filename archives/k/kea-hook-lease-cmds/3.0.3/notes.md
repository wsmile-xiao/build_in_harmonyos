# kea-hook-lease-cmds 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起由 Autotools 迁移；顶层 `meson.build`，`meson_version: '>=1.1.0'`）
- 编译日期: 2026-09-17
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，aarch64-linux-ohos，libc++，C++17）
- 工作副本: `/storage/Users/currentUser/Desktop/GPQworkspace/kea-hook-lease-cmds-3.0.3-wt`（分支 `feat/kea-hook-lease-cmds-3.0.3`；探索期基线 `origin/main@3e9c9ae236`，提交前按 W1 同步至 `origin/main@883c2777b7`，本分支提交均基于后者）
- 状态: built

## 软件定位
- 上游：ISC Kea 3.0.3（MPL-2.0），本库源码目录 `src/hooks/dhcp/lease_cmds/`
- 产物：`libdhcp_lease_cmds.so`（hook 插件，安装到 `lib/kea/hooks/`，由 kea-dhcp4/kea-dhcp6 运行时 dlopen）
- 命令 callout：`lease4-add/get/get-all/get-page/get-by-hw-address/get-by-client-id/get-by-hostname/del/update/wipe/resend-ddns/write/offer`、
  `lease6-*` 对应命令、`lease6-bulk-apply`、`leases4-committed`、`leases6-committed`
- 构建方式：Kea 3.0 起 Autotools → Meson，整棵源码树单工程构建；本配方构建上游树后
  只打包本插件 + 其 NEEDED 传递闭包中的 20 个 Kea 运行库

## 编译步骤

```bash
# 1) 生成构建环境（PkgConfigDeps + MesonToolchain，见 conanfile.py generate()）
conan install <probe> --output-folder=<out> -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 2) 配置
meson setup <builddir> <srcdir> --native-file=<out>/conan_meson_native.ini -Dtests=enabled
# 3) 构建（本插件 + 两个测试 target；实际编译 409 个 ninja 目标）
ninja -C <builddir> -j6 \
  src/hooks/dhcp/lease_cmds/libdhcp_lease_cmds.so \
  src/hooks/dhcp/lease_cmds/tests/dhcp-lease-cmds-lib-tests \
  src/hooks/dhcp/lease_cmds/libloadtests/dhcp-lease-cmds-libload-tests
# 4) 上游测试
meson test -v -C <builddir> dhcp-lease-cmds-lib-tests dhcp-lease-cmds-libload-tests

# 5) 配方固化
ohc-run.py refresh-patch --auto kea-hook-lease-cmds 3.0.3   # 生成 2 个补丁
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
ohc-run.py conan-verify kea-hook-lease-cmds 3.0.3
ohc-run.py finish kea-hook-lease-cmds 3.0.3 built
```

## 遇到的问题与解决方案

每个平台陷阱都用**对照组实验**（关闭单项适配后重跑 configure/编译）复现真实首个错误，
证据日志见 `reports/control-000N-*.log`。

| # | 首个错误（原始输出） | 根因 | 解决方案 | 对照证据 |
|---|------|------|----------|---------|
| 1 | `meson.build:17:0: ERROR: Unknown linker(s): [['llvm-ar']]`（rc=1，配置阶段最早期错误） | meson 对 clang 编译器默认用**裸名** `llvm-ar` 探测静态链接器（`compilers/detect.py: defaults['clang_static_linker'] = ['llvm-ar']`），而 MesonToolchain 未写出 `ar/ranlib`；本环境/CI worker 上裸名 exec 失败 | `generate()` 中从 `conf tools.build:compiler_executables` 的 `c` 编译器路径推导同目录 `llvm-ar`/`llvm-ranlib`，写入 `tc.binaries` | `control-0002-llvm-ar.log` |
| 2 | `meson.build:186:4: ERROR: Problem encountered: Unsupported system "harmonyos".`（rc=1） | OHOS 上 `platform.system()` 返回 HarmonyOS，meson 据此报告 host system=`harmonyos`；Kea 用 `build_machine.system()` 做平台分支，白名单只有 linux/freebsd/netbsd/openbsd/sun/darwin | 补丁 `0001-meson.build.patch`（+6 行）：顶层把 `SYSTEM == 'harmonyos'` 归一化为 `'linux'`，一处修改使全部子目录走 Linux 分支（含 `iface_mgr_linux.cc`/`pkt_filter_lpf.cc`） | `control-0001-harmonyos.log` |
| 3 | `meson.build:477:8: ERROR: Problem encountered: Boost TLS support broken.`（rc=1）；meson-log 首个编译错误 `boost/core/detail/sp_thread_sleep.hpp:73:5: error: use of undeclared identifier 'pthread_setcancelstate'` | OHOS musl 的 `sysroot/usr/include/pthread.h` 不声明 `pthread_setcancelstate()`，而 boost 1.85 在 `BOOST_HAS_PTHREADS && !__ANDROID__` 时无条件调用；`boost/asio/ssl.hpp` 头链必经 | `generate()` 注入 boost 官方逃生宏 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE` | `control-0003-boost-tls.log` |
| 4 | `Checking if "LOG4CPLUS_INITIALIZER_H" with dependency log4cplus runs: NO (127)` → `meson.build:824:24: ERROR: Unknown variable "log4cplus".`（rc=1） | meson 的特性探针是"编译并运行"；host 共享依赖 `liblog4cplus.so.9`（`shared=True`）不在配置期运行时 `LD_LIBRARY_PATH` 内（127 = 动态加载失败，原始输出 `Error loading shared library liblog4cplus.so.9`） | `generate()` 用 `Environment` 把各 host 依赖 `cpp_info.libdirs` 追加进 `LD_LIBRARY_PATH` 并 `save_script("conanbuildenv-kea-runtime")`（聚合进 conanbuild.sh，build 阶段自动 source） | `control-0004-log4cplus-ldpath.log` |
| 5 | `sysroot/usr/include/linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'`（ninja rc=1，`note: previous definition is here` 指向 `sys/socket.h:377`） | OHOS sysroot 的 `linux/socket.h`（bionic 派生）定义 `struct sockaddr_storage`，musl `sys/socket.h` 已提供；`linux/rtnetlink.h` 间接包含前者 | 补丁 `0002-src-lib-dhcp-iface_mgr_linux.cc.patch`（+13 行）：包含 netlink 头前 `#define sockaddr_storage __linux_uapi_sockaddr_storage`，include 后 `#undef`，守卫 `__linux__ && !__GLIBC__`（libc 鉴别宏，**不使用 `__OHOS__`**，规避 R8/PF5） | `control-0005-sockaddr-storage.log` |

## 源码修改

| 补丁 | 文件 | 行数 | 内容 |
|------|------|------|------|
| 0001-meson.build.patch | `meson.build` | +6/-0 | harmonyos → linux 平台名归一化 |
| 0002-src-lib-dhcp-iface_mgr_linux.cc.patch | `src/lib/dhcp/iface_mgr_linux.cc` | +13/-0 | netlink 头包含期间的 `sockaddr_storage` define-guard |

两处补丁均不含平台宏（PF5 通过）；补丁由 `refresh-patch --auto` 生成（R3）。

## 依赖版本

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| boost | 1.85.0 | 强制 | 1.90/1.91 缺 `boost/interprocess/...`、`circular_buffer` 等 Kea 强制头 |
| log4cplus | 2.2.0.1 | 强制 | Kea 日志后端（`shared=True`，配置期运行探针需 LD_LIBRARY_PATH） |
| openssl | 3.5.8.1 | 强制 | 默认 `crypto=openssl`（`CRYPTO_DEP`） |
| gtest | 1.17.0.1 | test_requires | `-Dtests=enabled` |
| meson | 1.11.0 | tool_requires | Kea 需 ≥1.10（boost 无 `libboost_system`，走 header-only 模块回退） |
| zlib | 1.3.1 | 传递 | boost 依赖 |

`conan download <dep> -r=ohpcd --only-recipe` 全部 exit_code=0（见 `reports/../` 会话记录，
实际输出：`boost/1.85.0` rc=0、`log4cplus/2.2.0.1` rc=0、`openssl/3.5.8.1` rc=0、
`gtest/1.17.0.1` rc=0、`meson/1.11.0` rc=0）；未使用本地缓存绕过、未使用 `--build=missing`。

可选后端 botan/krb5/mysql/postgresql/netconf 显式 `disabled`（制品仓无可消费依赖，默认亦不启用）。

## 验证结果

```bash
# 1) 探索阶段真实构建（ninja，409/409 目标，exit_code=0）
ninja -C build-r1 -j6 <lease_cmds hook + 2 个测试 target>            # reports/build.log

# 2) 上游测试（Meson 注册入口，实际执行）
meson test -v -C build-r1 dhcp-lease-cmds-lib-tests dhcp-lease-cmds-libload-tests
#   1/2 kea:dhcp-lease-cmds-libload-tests  OK   5.81s
#   2/2 kea:dhcp-lease-cmds-lib-tests      OK   2.16s
#   Ok: 2  Fail: 0                       exit_code=0     reports/upstream-meson-test.log
./dhcp-lease-cmds-lib-tests      → 24 tests / [  PASSED  ] 24 tests      exit_code=0
./dhcp-lease-cmds-libload-tests  → 355 tests / [  PASSED  ] 355 tests    exit_code=0
#   用例合计：379 执行 / 379 通过 / 0 失败 / 0 跳过（逐条名称见 reports/upstream-test-cases.txt）

# 3) 真实 conan create（全量干净构建 1432/1432 + build() 内上游测试 + test_package）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
#   Ok: 2 / Fail: 0（build 内 meson test）→ test_package 两用例通过 → rc=0
#   日志 reports/conan-create.log，退出码 reports/conan-create.rc = 0

# 4) conan-verify（G0-G4）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify kea-hook-lease-cmds 3.0.3
#   G0/G1/G2/G3/G4 全 PASS，verdict=PASS，可标记 published     reports/conan-verify-report.md

# 5) finish（10 步，rc=0）
python3 $SKILL_ROOT/scripts/ohc-run.py finish kea-hook-lease-cmds 3.0.3 built
#   Step4 conan-verify ✅ / Step5 W3 本地 CI 模拟 ✅ / Step6 finalize（仅 tar.gz、对话记录警告）
#   Step7 W5 540 对 doc↔kv 完整 / Step9 W2 无框架文件混入 / Step10 submit 就绪 ✅
#   → 编译收尾完成: kea-hook-lease-cmds 3.0.3 → built     reports/finish.log，reports/finish.rc = 0

# 6) W3 本地 CI 模拟（ci/conan/setup.sh + build_and_test.sh，真实 CI 脚本）
#   L0=pass（全部质量门禁）  L1=pass（上游测试 + test_package 实执行）
#   L2=skip（无 bin/，库包）  L4=pass（补丁无危险函数）  L5=pass（lib/ 有产物）
#   JC=pass  KC=pass  Total 1 / Success 1 / Pass rate 100%
#   .ci-result.json: exit_code=0，log_sha256 与 reports/w3-local-ci.log 实测一致
#   日志 reports/w3-local-ci.log
```

## 过程中的关键事件（首个错误 → 根因 → 修复 → 复验）

| # | 事件 | 首个错误 / 现象 | 根因 | 修复 | 复验 |
|---|------|----------------|------|------|------|
| 1 | test_package 首次编译失败（conan create 第 1 轮） | `test_lease_cmds_hook.c:40:42: error: use of undeclared identifier 'lease6'`（连带 5 errors，make Error 2） | 注释行 `/* lease_cmds registers the lease4-*/lease6-* … */` 中的 `lease4-*/` 提前闭合了 C 注释，后续文本被当作代码 | 改为 `/* lease_cmds registers the lease4- and lease6- command callouts. */` | `conan test test_package …` rc=0（reports/test-package.log）；随后完整 conan create rc=0 |
| 2 | conan-verify G2 第 1 轮超时 | `G2: FAIL`，`reports/conan-create.log` 内容为 `TIMEOUT` | conan_verify 内部 `conan create` 硬编码 `timeout=3600s`；当时机器负载 60-80（同机 6 个并发 conan create，非本包问题），全量构建 >3600s | 待负载回落后重跑（不改配方、不改框架） | 第 2 轮 G2 PASS，verdict=PASS（reports/conan-verify-report.md）；超时证据留档 reports/conan-verify-report-fail-timeout.md |
| 3 | finish W3 第 1 轮 JC 门禁失败 | `JC1/JC5: archives/c/cloog/0.21.1/.build-closed、.staging-verified` 被跟踪 → `JC_RESULT=fail` | 本分支尚无 commit，`git diff origin/main...HEAD` 为空 → junk_check 从 incremental 回落到 **full 模式（整仓扫描）**，命中 main 中既存的 cloog 历史遗留文件（非本包） | 用临时索引构造本包 `pr.diff` 并以 `JUNK_PR_DIFF` 提供，复现真实 CI 的 **prdiff 模式**（只检查本 PR 文件） | 第 2 轮 W3：JC_RESULT=pass、L0/L1/L4/L5 全 pass（reports/w3-local-ci.log） |

> 事件 2/3 均为环境或框架侧因素，未修改配方与源码；第 1 次失败日志均已留档
> （`conan-create-fail-1-testpackage-comment.log`、`conan-verify-report-fail-timeout.md`）。
> 完整 PR 文件原子性检查见 `reports/atomicity-check.md`。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/kea/hooks/libdhcp_lease_cmds.so` | lease-cmds hook 插件（SONAME `libdhcp_lease_cmds.so`，514 KB） |
| `lib/libkea-*.so*`（20 个库） | 插件运行时加载的 Kea 共享库（`readelf -d` NEEDED 传递闭包，已核对：闭包与配方 `kea_runtime_libs` 逐项一致，无缺失、无多余）+ soname 符号链接 |
| `licenses/COPYING` | 上游 MPL-2.0 许可 |
| 包大小 | 22 MB（`du -sh <pkg>`） |

## 注意事项

- 插件由 Kea 服务器 `dlopen()` 加载，**不是**被链接的库：包内 `cpp_info.libs` 为空，仅保留 `libdirs` 供运行期环境使用。
- 上游 Kea 全量测试套件包含需要特权/网络的用例，本配方只跑覆盖本插件的两个套件（`upstream_test_suites`）。
- 本包不产出命令行工具，R38 不适用（无需 `commands.json`）。
- **鸿蒙特有测试 1 项**（`test_package/test_ohos_platform.c`）：上游两个 gtest 套件只验证 hook 逻辑，
  不校验产物平台 ABI；该用例补充校验 OHOS aarch64/musl/libc++ 平台签名（EM_AARCH64、
  DT_NEEDED 为 `libc.so` 而非 glibc 的 `libc.so.6`、`libc++_shared.so`）与 OHOS 加载器可解析性。
---

**编译结束**: 2026-09-17 22:55
**最终状态**: built
