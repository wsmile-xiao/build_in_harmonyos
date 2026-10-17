# yojimbo 1.13.5 适配笔记（HarmonyOS PC / aarch64-linux-ohos）

## 概况
- networkprotocol 的游戏网络安全库（client/server UDP 加密协议，netcode.io + reliable.io 组合，内嵌最小 libsodium 提供 AEAD 加密）
- C++11 + C99，CMake ≥3.16 构建，v1.13.5 官方 tag
- **零外部依赖**：sodium/netcode/reliable/tlsf 以 OBJECT library 折入 libyojimbo.a，serialize 纯头文件
- 产物：libyojimbo.a（默认静态形态，808KB，vendored 四件全折入）

## 适配关键点

### 1. QUIC 族 musl 坑对照（第三件，对照 msquic 2.6.1 / gns 1.6.0 现场结论）
msquic 踩了两坑（pthread_setaffinity_np + CMSG_NXTHDR sign-compare），gns 一坑未踩
（affinity 无调用 + TOS 段被特性宏裁掉），yojimbo 同样**两坑均无命中面**：
- **pthread_setaffinity_np**：全树 grep 零调用
- **CMSG_NXTHDR**：全树零辅助数据遍历（无 recvmsg ancillary 路径）
- 平台检测：netcode.h / reliable.h / yojimbo_config.h 三处统一模式
  `#if defined(_WIN32) ... #elif defined(__APPLE__) ... #else → *_PLATFORM_UNIX`
  OHOS 直接落 UNIX 分支，走 BSD sockets + fcntl O_NONBLOCK + gettimeofday 纯 POSIX 路径
- 字节序：`__aarch64__` / `__LITTLE_ENDIAN__` 正确识别小端
- **零源码补丁**（与 gns 相同的结论：上游设计已覆盖 musl 兼容）

### 2. CMake 平台（无需 Linux 覆盖）
与 gns 不同：yojimbo 的 CMakeLists **没有平台匹配表**，不检查 CMAKE_SYSTEM_NAME 是否
在已知列表——ConanToolchain 映射 OHOS→HarmonyOS 原样可配（仅打印 "System is unknown
to cmake" 无害警告）。无需 `CMAKE_SYSTEM_NAME=Linux` 强制覆盖。

### 3. 版本与 vendored 校验（configure 期自校验）
- `dependencies.manifest`：serialize 1.16.2 / reliable 1.4.5 / netcode 1.4.8（floor 1.4.6）
- CMakeLists configure 期逐个读 vendored 头的 VERSION 宏与 manifest 比对——tarball
  自洽，无 submodule 风险（对照 gns 的空 submodule 坑，yojimbo 无此问题）

### 4. 构建形态
- `YOJIMBO_BUILD_TESTS=OFF`：交付库不含测试可执行文件（上游默认 ON 是给顶层开发者）
- `YOJIMBO_INSTALL=ON`：装 lib + include/（yojimbo 自有头 + sodium.h/netcode.h/
  reliable.h/serialize.h/tlsf.h——yojimbo.h 传递包含需要）
- 上游 strict FP：`-ffp-contract=off`（上游自动加，serialize.h 压缩浮点线格式需要）
- make -j1（R8/R9 共享 worker 并发约束）

### 5. 上游测试（本地全跑，N=2）
```
ctest --output-on-failure    → 2/2 PASS（总耗时 4.40s）
  1/2 yojimbo_test              Passed 4.36s   # [serialize][netcode][reliable][yojimbo] 四段
  2/2 yojimbo_custom_packet_io_test Passed 0.03s
```
- yojimbo_test 内部 53 个 test_* 函数全跑（serialize_test/netcode_test/reliable_test
  是 vendored C 库自带测试套件，经 SERIALIZE_ENABLE_TESTS/NETCODE_ENABLE_TESTS/
  RELIABLE_ENABLE_TESTS=1 编译进 test.cpp）
- **运行期 libc++**：交叉产物 NEEDED libc++_shared.so，须 `LD_LIBRARY_PATH=/system/lib64`
  （本机 OHOS 系统 so；SDK llvm/lib 下的同名 so 是链接器脚本会遮蔽真 so——profile
  已有该路径排序经验）
- CTest 注册数以 ctest -N 实测：N=2（client/server/loopback/soak 四个可执行文件中，
  仅 test 与 custom_packet_io_test 注册为 CTest 条目——examples 需对端、soak 无限跑）

### 6. test_package（消费者验证，2692 断言）
- 范式镜像上游 test_client_server_messages：Server::Start → Client::InsecureConnect
  （本地铸 connect token，全握手+libsodium AEAD）→ 双向 reliable-ordered 消息
  （TestMessage + TestBlockMessage 分片）→ 干净断连 → 双侧清零
- rule12 OHOS 行：`[OHOS] running on HarmonyOS: musl BSD-sockets + libsodium AEAD
  loopback session`（uname() 实读系统名/内核/架构，纯 POSIX 无平台宏）
- 输出：`PASSED: 2692 checks, 0 failed`，exit 0
- 命名坑：本地 `MaxClients` 常量与 yojimbo::MaxClients（yojimbo_constants.h）在
  `using namespace yojimbo` 下歧义——改名 MaxTestClients 解决
- conan API 坑：本仓 OHOS 适配版 conan 2.29.1 的 CMake.test() 无 output 参数且
  cli_args 转传给 cmake --build；正确写法 `cmake.ctest(cli_args=["--output-on-failure"])`

## 复验命令
```bash
conan create . -pr:h ~/.conan2/profiles/ohos-aarch64 -pr:b ~/.conan2/profiles/ohos-aarch64
# 上游测试（独立源码树）
cmake -G "Unix Makefiles" -DCMAKE_SYSTEM_NAME=HarmonyOS -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DCMAKE_BUILD_TYPE=Release -DYOJIMBO_BUILD_TESTS=ON <src> && cmake --build . -j1
LD_LIBRARY_PATH=/system/lib64 ctest --output-on-failure
```
