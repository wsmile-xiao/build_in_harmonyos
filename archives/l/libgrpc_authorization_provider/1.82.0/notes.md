# libgrpc_authorization_provider 1.82.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-18
- 编译器: clang/clang++ (Clang 15, OHOS SDK)
- 状态: built（待 CI）

## 背景

gRPC 模块拆分件（任务 #13212）：从 grpc v1.82.0 源码树构建鉴权模块库
`grpc_authorization_provider`（CEL 策略引擎：authorization policy 解析/
评估/rbac 转换），供需要 gRPC 授权策略的下游精确依赖。

**与 libgrpc_unsecure 的结构差异**：unsecure 件是 C 核心+C++ 绑定两个
独立 archive；本件的上游 target `grpc_authorization_provider` 本身就把
完整 C 核心（含 TLS/secure 源面）编进一个 archive——302 个源文件（对比
grpc_unsecure 451 个纯核心源）。因此：
- re2 + openssl 是**真链接依赖**（secure 源面引用其符号），非仅配置期
- 公开 API 面是 **C 核心**：include/grpc/grpc_security.h 的
  grpc_authorization_policy_provider_{static_data,file_watcher}_create /
  release（CEL 策略引擎）
- ⚠ 上游 C++ 绑定（grpcpp/security/authorization_policy_provider.h 的
  StaticDataAuthorizationPolicyProvider）**不编进任何库 target**——上游
  CMakeLists 只把 src/cpp/server/authorization_policy_provider.cc 编进
  authorization_policy_provider_test 测试程序（1.82 源码实测），链接期
  实锤（ld.lld undefined symbol）。需要 C++ 绑定的消费者用 grpc 主件

**模块拆分复用范式**：同 libgrpc_unsecure——复用 grpc/1.70.0 主件构建
体系（PR !6943），版本 1.70.0→1.82.0，目标收敛为 authorization 闭包，
手动打包。

## 编译步骤

```bash
conan create . -pr:h ~/.conan2/profiles/ohos-aarch64 -pr:b ~/.conan2/profiles/ohos-aarch64 --build=missing
```

关键设置与 libgrpc_unsecure 相同（见该件 notes），差异点：
- 构建目标：grpc_authorization_provider + gpr + upb 系 + address_sorting
- OPENSSL_ROOT_DIR 显式指定（secure 源面走 FindOpenSSL）
- 链接闭包含 re2/openssl

## 遇到的问题与解决方案

（同 libgrpc_unsecure 件的 4 个问题——共用补丁与范式；另加测试执行三坑）：

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 5 | grpc_authorization_policy_provider_test SIGABRT：fdopen 失败 | 测试用 repo 相对路径读 test_policies/*.json | 测试执行 cwd=source_folder（源码根） |
| 6 | grpc_audit_logging_test SIGABRT：gtest 捕获 stdout 写 /tmp 失败 | pinned gtest(52eb8108) Linux 分支硬编码 /tmp（Android 分支才读 TMPDIR） | 0007 补丁：gtest-port.cc CapturedStream Linux 分支读 TEST_TMPDIR/TMPDIR |
| 7 | TMPDIR 经 conan Environment 定义不生效 | self.run 的 env 参数包装方式不透传孙进程 | TMPDIR/LD_LIBRARY_PATH 直注 os.environ（try/finally 还原） |

## 产物（模块拆分闭包）

- `libgrpc_authorization_provider.a`（内嵌完整 C 核心含 security 源面）
- `libgpr.a` + `libupb_*_lib.a` ×12 + `libaddress_sorting.a`（链接闭包）
- 全量 `include/grpc/` + `include/grpcpp/` 公共头

## 依赖

- abseil-cpp/20260107.1、protobuf/33.6（同 unsecure 件）
- c-ares/1.34.6、zlib/1.3.1
- re2/2024-04-01、openssl/3.5.6（**真链接依赖**——secure 源面符号引用）

## 上游测试（rule4 真机执行，2026-09-18 补；2026-09-19 口径按审核裁决改全仓申报）

**申报口径（全仓）**：grpc 全仓 gtest 5267 TEST 宏（test/core 3817 + test/cpp 1450，
静态计数）——PR 统计表按此申报（覆盖审核实测口径 5260）。

**执行口径（模块关联）**：拆分件产物 = grpc_authorization_provider target 闭包。
执行链接该闭包的全部上游测试程序：**直链 grpc_authorization_provider 的全部
7 个测试程序**（CMakeLists target_link_libraries 实测核验），静态宏计数 152。
其余 5115 宏属 grpc 完整面测试（end2end/xds/grpc++/unsecure/插件），被测代码
不在本件产物内（PR 正文"减少原因"段逐类定性；unsecure 部分属 #10708 件范畴）。

**真机执行结果（conan create 内建，build 阶段构建+运行，7/7 程序 152/152 用例 100% 通过）**：

| 测试程序 | 实测用例 | 通过 | 失败 | exit |
|----------|---------|------|------|------|
| authorization_matchers_test | 48 | 48 | 0 | 0 |
| cel_authorization_engine_test | 5 | 5 | 0 | 0 |
| evaluate_args_test | 19 | 19 | 0 | 0 |
| grpc_audit_logging_test | 5 | 5 | 0 | 0 |
| grpc_authorization_engine_test | 15 | 15 | 0 | 0 |
| grpc_authorization_policy_provider_test | 7 | 7 | 0 | 0 |
| rbac_translator_test | 53 | 53 | 0 | 0 |
| **合计** | **152** | **152** | **0** | - |

**执行机制**（配方 build() 内建，CI 可复现）：
- gRPC_BUILD_TESTS=ON + gRPC_BUILD_CODEGEN=ON（本机 native aarch64 OHOS——
  protoc/grpc_cpp_plugin 编出即原生可跑）
- conandata 声明 7 个测试支撑子模块源（googletest/cel-spec/googleapis/xds/
  opencensus-proto/protoc-gen-validate/envoy-api——tarball 内空子模块，
  按 v1.82.0 pin commit 填充，离线可配）
- cmake --build --target 收敛 7 测试程序 + grpc_test_util
- cwd=源码根运行（policy_provider 测试读 repo 相对路径的测试数据文件）
- TMPDIR 直注 os.environ（audit_logging 的 gtest stdout 捕获需要，0007 补丁配套）
- 逐程序直跑，gtest 汇总解析写 test_results/upstream_tests_summary.txt

**test_package 冒烟（C 核心 API 三段验证）**：
① 合法 CEL 策略 → static_data_create 成功 + release（引擎真构造）
② 非法策略 → create 拒绝并返回错误码（解析器真运行，非 stub）
③ file_watcher 指向不存在文件 → 干净拒绝（错误路径）

## 源码修改（7 个补丁——1-6 与 libgrpc_unsecure 共用，0007 本件专属）

- 0001-thd-pthread-cancel.patch / 0002-abseil-cpp-cmake-alias.patch /
  0003-cares-cmake-target.patch / 0004-ssl-cmake-target.patch /
  0005-tmpfile-tmpdir.patch / 0006-zlib-cmake-target.patch
- 0007-gtest-captured-stream-tmpdir.patch：third_party/googletest
  gtest-port.cc，stdout 捕获临时文件读 $TEST_TMPDIR/$TMPDIR（OHOS /tmp 只读）

## 验证结果

```bash
conan create . -pr:h ~/.conan2/profiles/ohos-aarch64 -pr:b ~/.conan2/profiles/ohos-aarch64 --build=missing
# libgrpc_authorization_provider/1.82.0 编译通过（0 error），test_package 通过
# 1/1 Test #1: test_package Passed 0.03 sec（100% 通过）
# 上游授权闭包测试：7 程序 152/152 用例通过（见"上游测试"节明细表）
```

真机直跑输出（CEL 引擎三段验证）：
```
grpc core version: 55.0.0
valid policy: provider created and released（合法策略 → 引擎构造成功）
invalid policy: rejected (code=3, parser active)（非法策略 → 解析器拒绝）
file watcher (missing file): rejected (code=3)（不存在文件 → 干净拒绝）
test_package: OK
```
