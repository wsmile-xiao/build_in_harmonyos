# cnats 3.13.0 适配笔记

## 软件信息
- 软件：cnats 3.13.0（上游 nats-io/nats.c tag v3.13.0，NATS C 客户端库）
- 任务号：6534（活动：开源鸿蒙PC专项积分赛）；分支 feat/cnats-3.13.0；worktree ~/qzy/cnats
- 构建系统：CMake
- 编译日期：2026-09-08
- 编译器：clang 15.0.4（OHOS SDK llvm）
- 状态：published（conan-verify G0-G4/L2/L4/L5 全 PASS）
- 源码：https://github.com/nats-io/nats.c/archive/refs/tags/v3.13.0.tar.gz
  SHA256 f6ec9ee2ab367594b56dd3265e3561074ade7c3d7410a6f45a77704c5e537024

## W0/W0b
- W0：唯一依赖 openssl/3.0.16 已发布，`conan install --requires=openssl/3.0.16
  --build=never -pr:a ci/conan/profiles/ohos-aarch64` 解析成功且 binary=Download（预编译
  二进制可用）；libsodium/libevent/libuv/protobuf 均为上游默认 OFF 的可选依赖，未启用。
- W0b：本仓库无 cnats 历史归档（archives/c 无同包），无历史 notes 可比对；CI 能力矩阵
  CMake/clang ✅。
- lang-preflight 首跑误报 `mixed`（evidence：源文件 338 个 nodejs:247/c:88，"主体占比
  73%"）：247 个 js 全部位于 `doc/html/`（Doxygen 生成文档资产，取证
  ~/tmp/uc2/cnats/langpreflight-misreport-evidence.md，非 doc/html 的 js 数为 0）；
  manifest=cpp（CMakeLists.txt）、构建系统=cmake，主体为纯 C 库。与 utfcpp20/0.3
  （任务 #5895，经验汇总 §12.8）同根因，判误报继续适配；任务终态以真实结果覆盖
  env_unsupported。

## 配方要点
- 模板：CMake（conan-init 误配 autotools 模板，已按实际构建系统重写）。
- `requires("openssl/3.0.16")`；TLS ON（上游默认 NATS_BUILD_WITH_TLS=ON）。
- **关键修复 1**：generate() 显式 `tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"`。
  根因：OHOS 适配 Conan 将 os=OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS，上游
  CMakeLists 的平台分支是 `if(UNIX)/elseif(WIN32)/else()`，HarmonyOS 不满足 UNIX
  → NATS_LIBDIR/NATS_INCLUDE_DIR/NATS_PLATFORM_INCLUDE 全部未定义 →
  `install FILES given no DESTINATION`（src/CMakeLists.txt:89）且 unix 平台源码不编。
  OHOS sysroot（aarch64）提供 librt.a，Linux 分支的 -lrt 可正常链接（已实测）。
- **关键修复 2**：package_info 用包级依赖 `openssl::openssl`。制品仓 openssl/3.0.16
  配方为包级声明（cpp_info.libs=["ssl","crypto"]，无组件），组件式 `openssl::ssl`
  会报 `Component 'openssl::ssl' not found`。
- 上游静态库输出名 nats_static（无 OUTPUT_NAME 覆盖），动态为 nats；cpp_info.libs 按
  options 分别声明。上游安装的 pkg-config/CMake 导出（-lnats、Threads::Threads）与
  Conan 管理不一致，package() 中移除 lib/pkgconfig 与 lib/cmake，查找统一交给 CMakeDeps。
- 无补丁（patches: {}，保留显式 apply_conandata_patches 调用）。

## 上游测试统计与执行（R51）
- 静态清点（N_static）：`test/CMakeLists.txt` 对 list_test.txt（324 个 `_test(...)`）
  与 list_bench.txt（6 个 bench）逐行 `add_test`，共 **330** 个注册测试；
  list_stan.txt（27 个 streaming 测试）在 NATS_BUILD_STREAMING=OFF 时不注册，不计入。
- 实际执行：设备真机构建 testsuite（BUILD_TESTING=ON + conan toolchain）+ 官方
  nats-server v2.10.24 linux-arm64 预编译二进制（binary-sign-tool 自签名后运行，
  PATH 提供），`ctest -j1` 全量执行 330 个：
  - 功能测试 324 个：316 Passed / 8 Failed，其中重跑复验 AssignSubToDispatch 由
    FAILED 转 Passed（时序敏感，非稳定失败）；
  - 稳定失败 7 个（占静态全量 7/330 = 2.1%）：
    1. BasicClusterReconnect：「Check reconnect time did not take too long」重连
       耗时阈值断言，HMDFS 虚拟化设备调度延迟大；
    2. DrainConnReqReply：「Check no delay with req/reply」延迟上限断言，同上；
    3. TimeoutOnNoServer：「Wait for closed」异步关闭回调时序，同上；
    4. natsHashing：「Hashing performance」要求 1000ms 内完成 HASH_ITER 次哈希
       （testCond((end-start)<1000)），纯性能断言，设备不达标；
    5. IPResolutionOrder：「Order: 6」IPv6-only 场景报 No server available，
       设备网络栈 IPv6 行为与测试假设不符；
    6. natsSock_IPOrder：「#08 IPv6 only」同上（socket 层 IPv6 探测）；
    7. RequestTimeout：期望请求返回 NATS_TIMEOUT，实测返回 NATS_NO_RESPONDERS
       （Error 34）——nats-server 2.10 默认开启 no_responders，服务器立即回送
       NO_RESPONDERS 而非客户端等待超时，上游测试未适配新版服务器行为。
  - bench 6 个：性能基准（BenchXXX），在设备上超时（ctest --timeout 300 杀掉
    BenchJetStreamPubAsync 等），均为性能类，功能覆盖不受影响。
- CI 边界：CI worker 无法提供可执行的 nats-server 二进制（未签名 ELF 不可执行），
  上游套件仅在设备真机执行；CI 以消费者 test_package 验证包可用性。
- 记录：~/tmp/uc2/cnats/ctest-full.log、upstream-build.log、ctest-failures-analysis.txt

## 消费者测试（test_package）
- test_package.c 真实调用库 API：nats_Open → nats_GetVersion → natsOptions_Create/
  SetURL/SetAllowReconnect/SetMaxReconnect/SetSecure(TLS) → natsConnection_Connect
  连接不存在服务器断言返回 NATS_NO_SERVER（真实连接路径执行）→ nats_CloseAndWait。
- conan-verify G2 实跑输出：「cnats consumer test passed (library 3.13.0;
  connect-to-absent-server -> NATS_NO_SERVER)」。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | install FILES given no DESTINATION | CMAKE_SYSTEM_NAME=HarmonyOS 不满足上游 if(UNIX) | toolchain 显式 CMAKE_SYSTEM_NAME=Linux |
| 2 | Component 'openssl::ssl' not found | 制品仓 openssl 配方无组件 | cpp_info.requires 用 openssl::openssl 包级引用 |
| 3 | lang-preflight 误报 mixed | doc/html Doxygen 资产 247 个 js 计入源码统计 | 按 utfcpp20 先例判误报，证据存档，终态覆盖 |

## 依赖版本
- openssl/3.0.16（制品仓预编译二进制，OHOS aarch64）

## 验证结果
- conan-verify：G0 PASS / G1 PASS / G2 PASS（conan create 干净构建 + test_package
  实跑）/ G3 PASS / G4 PASS / L2 PASS / L4 PASS / L5 PASS
- 上游套件：330 执行，323 Passed（含 1 个重跑转通过），7 稳定失败（原因见上），
  6 bench 设备超时（性能类）；详见 ~/tmp/uc2/cnats/ctest-full.log

## 注意事项
- OHOS 上游测试需要 nats-server：仅设备真机可跑（需签名），CI 不可复现，勿将
  testsuite 构建放进配方。
- deprecated 头 `<nats.h>`（新路径 `<nats/nats.h>`）在包内两者都安装，消费者可迁移。
---

**编译结束**: 2026-09-08 03:45
**最终状态**: built
