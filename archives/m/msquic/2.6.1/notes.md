# msquic 2.6.1 适配笔记（HarmonyOS PC / aarch64-linux-ohos）

## 概况
- 微软 QUIC 协议栈实现，纯 C + CMake，v2.6.1 官方 tag
- TLS provider：openssl（conan `openssl/3.5.8.1`，上游要求 >= 3.5.0）
- 产物：libmsquic.so.2.6.1（SONAME libmsquic.so.2），NEEDED 仅 libc.so

## 适配关键点

### 1. TLS 子模块缺失 → conan openssl 外链
上游 release tarball 的 submodules/openssl 是空目录（git submodule 未打包）。
走 `QUIC_TLS_LIB=openssl` + `QUIC_USE_EXTERNAL_OPENSSL=ON` +
`QUIC_OPENSSL_ROOT_DIR=<conan openssl package_folder>`，CMake 用 FindOpenSSL
找到 3.5.8（>= 3.5.0 满足）。openssl 静态库链入 .so，运行时零额外依赖。

### 2. musl 无 pthread_setaffinity_np（补丁 0001）
platform_posix.c 的 CxPlatThreadCreate 尾部对非 Android 平台调用
`pthread_setaffinity_np`（glibc 扩展，musl 未提供）。对齐上游自己对
bionic 的处理（`#if !defined(__ANDROID__)`），加 `&& !defined(__OHOS__)`
跳过。上游在同一函数前部已有 `#ifdef __GLIBC__` 守卫 attr 系亲和调用，
说明该逻辑本来就按 libc 分支设计。亲和性是性能优化非功能必需。

### 3. musl CMSG_NXTHDR 宏符号比较缺陷（补丁 0002/0003）
musl sys/socket.h 的 `CMSG_NXTHDR` 展开为
`__CMSG_LEN(cmsg) + sizeof(struct cmsghdr) >= __MHDR_END(mhdr) - (unsigned char *)(cmsg)`，
左边 size_t（unsigned long）、右边 ptrdiff_t（long）。
msquic 全工程 `-Werror -Wsign-compare`，datapath_linux.c / datapath_epoll.c
的 `CMsg = CMSG_NXTHDR(...)` 在宏展开处报 sign-compare。
glibc 的同名宏做了 cast 清理，所以这是 musl 专属坑。
处理：两个编译单元头部加 `#pragma clang diagnostic ignored "-Wsign-compare"`。
（datapath_kqueue.c 是 BSD、datapath_iouring.c 默认不编译、winuser 是 Windows，
Linux 路径只需处理这两个文件。）

### 4. CMake 生成器/版本
- 上游声明 `cmake_minimum_required(3.16/3.20)`，CI/本地 cmake 4.1.2 需要
  命令行传 `CMAKE_POLICY_VERSION_MINIMUM=3.5`
- 不允许 in-source build，conan basic_layout 天然分离
- `QUIC_EMBED_GIT_HASH=OFF`：tarball 非 git repo，避免 get_git_current_hash 失败
  （该失败本身不致命，上游只是关掉 SOURCE_LINK）

### 5. 能力探测结论（OHOS SDK 26.0.0.18 sysroot）
CMake check 全绿：`UDP_SEGMENT`（netinet/udp.h 103）、
`SO_ATTACH_REUSEPORT_CBPF`（sys/socket.h 51）、`sendmmsg/recvmmsg`、
`_SC_PHYS_PAGES`、`sysconf`、epoll/eventfd 都在 musl/sysroot 中。
意味着 UDP GSO、REUSEPORT 负载均衡、批量收发等 Linux datapath 高级特性
在 OHOS 上探测通过并编入。未启用 io_uring（QUIC_LINUX_IOURING_ENABLED=OFF，
默认即 OFF）。

### 6. 日志
`QUIC_ENABLE_LOGGING=OFF`（lttng-ust 在 OHOS 无）→ QUIC_EVENTS_STUB/
QUIC_LOGS_STUB，公共 ABI 不变。CLOG sidecar 头在 tarball 里已预生成，
不需要 clog 工具。

## 测试
- 上游测试：3 个 gtest 二进制（msquictest 端到端 / msquiccoretest /
  msquicplatformtest），构建需 googletest submodule（tarball 空目录）→
  CI 离线不可构建，本地联网补跑（见 PR 正文测试段）
- test_package：真实 API 生命周期测试（Open2→GetParam→Registration→
  Configuration→Close），验证 musl pthread worker 线程启动

## 复现命令
```
conan create archives/m/msquic/2.6.1 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
