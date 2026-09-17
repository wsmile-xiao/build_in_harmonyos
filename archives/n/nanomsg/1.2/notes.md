# nanomsg 1.2 适配笔记

## 编译环境
- 构建系统: cmake（顶层 CMakeLists.txt，project(nanomsg C)）
- 编译日期: 2026-09-15
- 编译器: clang 15 (aarch64-unknown-linux-ohos, OHOS SDK 26.0.0.18)
- 状态: built（配方 conan create 验证通过后升级）

## 版本与来源
- 上游 tag: `1.2`（精确格式，无 v 前缀；tag commit a081f1720f57，2017-09-26 发布）
- tarball: https://github.com/nanomsg/nanomsg/archive/refs/tags/1.2.tar.gz
- sha256: 6ef7282e833df6a364f3617692ef21e59d5c4878acea4f2d7d36e21c8858de67
- 注意：`.version` 文件内容为 `1.1.5`（上游发布时未更新，源码包真实版本即 tag 1.2，nn.h NN_VERSION 为 ABI 版本 5.0.0——目录名/配方版本按 tag 1.2）

## 编译步骤（本地实机验证）

```bash
SDK=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native
mkdir build && cd build
CMAKE_POLICY_VERSION_MINIMUM=3.5 cmake -G "Unix Makefiles" \
  -DCMAKE_SYSTEM_NAME=HarmonyOS \
  -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_C_COMPILER=$SDK/llvm/bin/clang \
  -DCMAKE_C_COMPILER_TARGET=aarch64-linux-ohos \
  -DCMAKE_SYSROOT=$SDK/sysroot \
  -DNN_ENABLE_DOC=OFF -DNN_TESTS=ON \
  -DCMAKE_INSTALL_PREFIX=<prefix> <src>
make -j1
make install
ctest --output-on-failure   # LD_LIBRARY_PATH 指向 install lib/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 报 "Assertion failed; this path is unreachable"（src/CMakeLists.txt:259） | CMAKE_SYSTEM_NAME=HarmonyOS 不匹配任何平台分支，UNIX 变量为假 → POSIX 源文件路径分支缺失 | patch 顶层 CMakeLists.txt 增加 HarmonyOS 分支：`NN_HAVE_HARMONYOS` + `NN_HAVE_LINUX` + `set(UNIX TRUE)`（与 Android 分支同构） |
| 2 | cmake_minimum_required(2.8.12) 与新版 cmake 策略不兼容 | 上游 2017 年老包，cmake 3.27+ 拒绝 <3.5 声明 | patch 提升 cmake_minimum_required 到 3.5；命令行同时传 CMAKE_POLICY_VERSION_MINIMUM=3.5 兜底 |
| 3 | 文档构建找 asciidoctor | CI/本地均无 asciidoctor | NN_ENABLE_DOC=OFF（库本体无文档依赖，man 页与库无关） |

## 源码修改

- patches/0001-CMakeLists.txt.patch：
  - cmake_minimum_required 2.8.12 → 3.5
  - 新增 HarmonyOS 平台分支（NN_HAVE_HARMONYOS + NN_HAVE_LINUX + UNIX TRUE）
  - 平台特有，guard 无需（仅加平台定义，不改通用逻辑）

## 平台能力探测结果（HarmonyOS sysroot）

epoll/poll/pipe/pipe2/accept4/socketpair/CLOCK_MONOTONIC/MSG_CONTROL/GCC atomic builtins
全部可用（check_function_exists 实测），线程库 pthread 提供 sem_wait → NN_USE_EPOLL +
NN_USE_EVENTFD（若 eventfd 探测通过）/NN_USE_PIPE 路径正常编译。

## 上游测试（upstream-testing.md 硬纪律——真实执行）

- 注册测试数：**43**（ctest -N 实测；win_sec_attr 为 WIN32 专属不注册）
  - 传输套件 8：inproc/inproc_shutdown/ipc/ipc_shutdown/ipc_stress/tcp/tcp_shutdown/ws
  - 协议套件 6：pair/pubsub/reqrep/pipeline/survey/bus
  - 功能套件 29：async_shutdown/block/term/timeo/iovec/msg/prio/poll/device/device4~
    device7/emfile/domain/trie/list/hash/stats/symbol/separation/zerocopy/shutdown/cmsg/
    bug328/bug777/ws_async_shutdown/reqttl/surveyttl
- 实测结果：**39/43 通过（91%）**（HarmonyOS PC aarch64 实机，LD_LIBRARY_PATH 指向
  install lib，ctest 逐项 --output-on-failure）
- 失败 4 项与豁免证据：
  - `ipc`：Failed bind to "ipc://test.ipc": Operation not permitted [1] (tests/ipc.c:63)
  - `ipc_shutdown`：Failed bind to "ipc://test-shutdown.ipc": Operation not permitted (tests/ipc_shutdown.c:94)
  - `ipc_stress`：Assertion failed: nn_bind(sock, SOCKET_ADDRESS) >= 0 (tests/ipc_stress.c:50)（同 bind EPERM）
  - `separation`：Failed bind to "ipc://test-separation.ipc": Operation not permitted (tests/separation.c:81)
  - **定性：平台限制非源码缺陷**——独立最小复现程序（socket(AF_UNIX,SOCK_STREAM)+bind）
    同样返回 `Operation not permitted (errno=1)`，证明 HarmonyOS PC 当前系统策略禁用
    本地 AF_UNIX socket bind（与 nng 1.8.0 归档记录的同类限制一致）。tcp 传输全部通过。
- perf 工具（inproc_lat/inproc_thr/local_lat 等 6 个）为基准工具非测试，不在 N 计数内。

## 依赖版本

- 无 conan 依赖（NN_REQUIRED_LIBRARIES 仅系统 pthread，musl libc 内建）
- W0 检查：nanomsg/1.2 无前置依赖需要发布

## 验证结果

```bash
# conan create（CI 同源验证，见 .ci-result.json）
conan create . -pr:h=<ohos-aarch64 profile> -pr:b=同 --build=missing
# 上游测试
ctest --output-on-failure
#     39/43 tests passed, 91%
# 消费者测试 test_package
./test_nanomsg   # inproc pair echo + tcp loopback echo ok
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（CMake，shared 默认 ON） |
| conandata.yml | 源码 URL+sha256、patch 声明 |
| patches/0001-CMakeLists.txt.patch | 平台识别补丁 |
| test_package/ | 消费者验证（inproc+tcp 回环） |
| manifest.yaml / notes.md | 元数据与笔记 |

## 注意事项

- 本件是 nanomsgxx 0.2（任务 #6652）的直接前置依赖：nanomsgxx 链接 libnanomsg
  （pkg-config nanomsg / find_package(nanomsg)），本包发布后 nanomsgxx 可继续。
- 产物 libnanomsg.so.5.0.0（NN_ABI_VERSION 5），nanocat 工具随 bin 安装。
- 上游 1.2 是最后一代 C 实现的 nanomsg（后继是 nng）；nanomsgxx 绑定的 API 即本版。
- ipc:// 传输在当前系统策略下不可用（bind EPERM），inproc/tcp/ws 可用——消费者如需
  ipc 需等系统放开 AF_UNIX bind 权限。

---

**编译结束**: 2026-09-15
**最终状态**: built
