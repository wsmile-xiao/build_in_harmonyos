# gamenetworkingsockets 1.6.0 适配笔记（HarmonyOS PC / aarch64-linux-ohos）

## 概况
- Valve 的游戏网络库（可靠 UDP 传输，SteamNetworkingSockets 技术提取）
- C++11 + C99，CMake 构建，v1.6.0 官方 tag
- 依赖：openssl（crypto）+ protobuf（wire 协议）
- 产物：libGameNetworkingSockets_s.a（默认静态形态）

## 适配关键点

### 1. QUIC 族 musl 坑对照（对照 msquic 2.6.1 现场结论）
gns 与 msquic 同属 Linux epoll/datagram 系，但实测**两坑都不踩**：
- **pthread_setaffinity_np**：gns 源码零 affinity 调用（grep 验证），无需 patch
- **CMSG_NXTHDR sign-compare**：socketthread.cpp 的 TOS 辅助数据遍历段在
  `#if PlatformSupportsRecvMsg() && PlatformSupportsRecvTOS()` 内，OHOS 上
  `PlatformSupportsRecvTOS()` 因 IP_RECVTOS 探测失败走 false 分支——整段被
  预处理器裁掉，musl 宏的 signed/unsigned 混用根本不进编译单元
- 根因差异：msquic 无条件启用 TOS 读取（datapath_linux.c 直接 CMSG 遍历），
  gns 用特性宏守卫且 musl 下自动降级——上游设计差异决定坑的命中

### 2. CMake 平台表（CMAKE_SYSTEM_NAME=Linux）
上游 `set_target_common_gns_properties()` 平台匹配表硬编码
Linux/Darwin/FreeBSD/OpenBSD/Windows，HarmonyOS 不在表内直接 FATAL_ERROR
（`Could not identify your target operating system`）。CMakeToolchain 会把
OHOS 映射为 HarmonyOS，须在 toolchain variables 强制 `CMAKE_SYSTEM_NAME=Linux`
（OHOS = Linux 内核 + musl 用户态，LINUX define + epoll 路径正确）。
同款范式：msquic（CX_PLATFORM=linux）、brpc（E092）。

### 3. protobuf 接线（制品仓 cmake_find_mode=none 范式）
- protobuf/33.6.1 制品仓包声明 `cmake_find_mode=none`，CMakeDeps 不生成
  config——须显式 `Protobuf_DIR`/`utf8_range_DIR`/`absl_DIR` 指向已装
  config 文件（grpc/brpc 配方同款接线）
- `protobuf_generate_cpp` 在 configure 期调用 protoc 生成 .pb.cc/.pb.h
  （3 个 .proto：messages_certs/messages/messages_udp）
- **protoc 是 OHOS 目标二进制**：本机同为 OHOS arm64 可直接执行，但其
  依赖的 libc++_shared.so 不在默认搜索路径——build env 前插工具链
  libc++ 目录到 LD_LIBRARY_PATH（`~/ohos-sdk/llvm/lib/aarch64-linux-ohos/c++`，
  brpc 配方同款 `_toolchain_libcpp_dir()` 探测）

### 4. submodule 空目录 → 功能面裁定（2026-09-18 纠偏）
上游 release tarball 不含 submodule（git submodule 未打包）：
- `src/external/webrtc`（空）：**USE_STEAMWEBRTC** 依赖，巨物库无法引入（保持 OFF）
- `src/external/abseil`（空）：steamwebrtc 的 pin 是 lts_2020_02_25，与
  protobuf 33.6.1 所需 abseil 20260107 ABI 冲突（仅 USE_STEAMWEBRTC=ON 才引用）
- `src/external/vjson`（空）：BUILD_TOOLS（certtool）依赖
处置：`USE_STEAMWEBRTC=OFF` + `BUILD_TOOLS=OFF` + **`ENABLE_ICE=ON`（上游默认）**。
纠偏记录：初版误设 ENABLE_ICE=OFF——复查 src/CMakeLists.txt 发现 ENABLE_ICE 仅加
`STEAMNETWORKINGSOCKETS_ENABLE_ICE` 编译定义 + 启用纯 POSIX native ICE client
（steamnetworkingsockets_ice_client.cpp，RFC8489 子集），**不需要任何 submodule**；
需要 webrtc submodule 的是 USE_STEAMWEBRTC（默认 OFF）。ENABLE_ICE=ON + BUILD_TESTS=ON
实测全量构建通过（含 test_p2p 链接 static_mock），交付库恢复上游默认 P2P 面。

### 4b. p2p 测试豁免（上游注册第 4 项）
`GameNetworkingSockets_test_s`（mock 网络框架）在 `BUILD_TESTS AND BUILD_STATIC_LIB
AND ENABLE_ICE` 时构建，test_p2p.py 驱动 `--ice-implementation 1`（native）全套
NAT 穿透场景。本地实测阻塞在环境层：脚本要求 5 个 mock IPv6 loopback 别名
（fd7f:0:100::1/2/3、fd7f:0:1::2、fd7f:0:2::2）可 bind——本机 bind 全部
Errno 99，加别名需 root（`ifconfig lo inet6 add ...` → ioctl 8916 Permission
denied，OHOS 无 root，ip 命令也不可用）。p2p 二进制本身构建成功（上游注册 N=4
实测：ctest -N 列 connection_quick/connection_soak/crypto/p2p）。

### 5. 构建选项
- BUILD_SHARED_LIB=OFF + BUILD_STATIC_LIB=ON（库形态交付；shared 亦可编）
- 上游 `cmake_minimum_required(3.15)`，CI/本地 cmake 4.x 需命令行传
  `CMAKE_POLICY_VERSION_MINIMUM=3.5`
- USE_CRYPTO 默认 OpenSSL，conan openssl/3.5.8.1 满足（EVP_MD_CTX_free
  符号检查通过）
- make -j1（R9）

## 上游测试（真跑记录）
- 上游默认形态 `ctest -N`：**4 项注册**（connection_quick / connection_soak / crypto / p2p，ENABLE_ICE=ON）
- crypto：PASS（2.09s，AES-GCM/SHA/ed25519/curve25519 全向量化路径）
- connection_quick：PASS（206.05s，回环 UDP 可靠传输全套）
- connection_soak：PASS（4948.81s，20+ 网络条件组合长测浸泡——带宽/丢包/延迟/乱交矩阵）
- p2p：**豁免**（p2p 二进制构建成功；test_p2p.py 启动即退——mock IPv6 loopback
  别名不可 bind，加别名需 root，见 4b；单报错原文：
  `ERROR: the following addresses required by the mock network are not
  bindable: fd7f:0:100::1 ... Run 'sudo ./test_p2p.py --setup-mock-ips'`）
- 本地探索目录：`~/tmp/gns-explore/build-test`（初版 ICE=OFF）/`~/tmp/gns-explore/build-ice`（ICE=ON 全量）
