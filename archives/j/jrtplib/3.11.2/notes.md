# jrtplib 3.11.2 适配笔记

## 编译环境

- 构建系统: CMake（上游 `cmake_minimum_required(VERSION 2.8)`）
- 编译日期: 2026-09-15
- 编译器: Clang 15.0（OHOS aarch64 原生构建）
- 目标平台: aarch64-unknown-linux-ohos
- 状态: published
- 源码格式: tar.bz2（`conan get` 原生支持）

## 上游信息

- 官方主页: https://research.edm.uhasselt.be/jori/jrtplib
- 源码包: https://research.edm.uhasselt.be/jori/jrtplib/jrtplib-3.11.2.tar.bz2
- sha256: `2c01924c1f157fb1a4616af5b9fb140acea39ab42bfb28ac28d654741601b04c`（与 Homebrew homebrew-core `Formula/j/jrtplib.rb` 交叉核对一致）
- 开发仓库已从 GitHub（j0r1/JRTPLIB）迁移至 https://codeberg.org/j0r1/JRTPLIB；发行包仍以官网 tarball 为准
- License: MIT（`LICENSE.MIT` 已随包发布到 `licenses/`）

## 编译步骤

jrtplib 3.11.2 使用 CMake 构建，线程支持依赖同作者的 JThread 库（制品仓已有 `jthread/1.3.3`，
配方以 `transitive_headers/transitive_libs` 引用，因为 `rtppollthread.h` 公开 `#include <jthread/jthread.h>`）。

Conan 配方关键配置（`generate()`）：

```cmake
-DCMAKE_POLICY_VERSION_MINIMUM=3.5   # 上游最低声明 2.8，新 CMake 兼容层（复用 jthread 经验）
-DJTHREAD_ENABLED=ON                 # 线程支持（Conan 前缀路径可被上游 cmake/FindJThread.cmake 发现）
-DJRTPLIB_COMPILE_TESTS=ON           # 编译 tests/ 全部 14 个程序
-DJRTPLIB_COMPILE_EXAMPLES=ON        # 保持上游默认，编译 8 个示例（仅编译，不安装不运行）
-DJRTPLIB_WARNINGSASERRORS=OFF       # clang 被判为 GNU 系会触发 -Werror，2020 年代码在 clang 15 下必挂
-DJRTPLIB_USE_BIGENDIAN=OFF          # 仅交叉编译时生效；aarch64 为小端
-DSRTP_ENABLED=OFF -DSRTP2_ENABLED=OFF  # 无 libsrtp 依赖，显式关闭
```

产物：`lib/libjrtp.a` + `lib/libjrtp.so`（上游在非 MSVC 平台恒同时构建静态与动态库，
与 `shared` 选项无关）、头文件 `include/jrtplib3/*.h`、`lib/pkgconfig/jrtplib.pc`。
`package_info` 声明 `libs=["jrtp"]`，CMake 目标 `jrtplib::jrtplib`，OHOS 下追加系统库 `pthread`。

## 上游测试清点（tests/，共 14 个，无 ctest 注册，均无自动化 harness）

| # | 程序 | 是否可自动化 | 说明 |
|---|------|-------------|------|
| 1 | timetest | 可 | 纯 RTPTime 运算 + 10 秒等待，exit 0；断言输出含 `Microseconds:` |
| 2 | timeinittest | 可 | 构造 `RTPUDPv4Transmitter(0)` + 打印，无阻塞，exit 0 |
| 3 | testexttrans | 可 | 假 transmitter 注入约 100 万包，输出以 `Writing packet 1048000` 收尾 |
| 4 | testrawpacket | 可 | 回环自发自收（127.0.0.1:5000，约 30 秒），输出含 `Valid RTP packet` |
| 5 | testmultiplex | 否 | 需手动输入本端/对端端口与 IP（stdin 交互） |
| 6 | testexistingsockets | 否 | 需预置 socket 描述符与对端配合 |
| 7 | testautoportbase | 否 | 需手动输入端口、对端地址与包数 |
| 8 | srtptest | 否 | 需 libsrtp 且需对端安全会话配合（本配方关闭 SRTP） |
| 9 | rtcpdump | 否 | 需指定监听端口并等待外部 RTCP 流（被动阻塞） |
| 10 | readlogfile | 否 | 需外部提供 RTP 日志文件作为参数 |
| 11 | abortdesctest | 否 | 需双端 socket + 手动 abort 时序配合 |
| 12 | abortdescipv6 | 否 | 同上，且需 IPv6 环境 |
| 13 | tcptest | 否 | 需手动输入本端/对端 TCP 端口与 IP |
| 14 | sigintrtest | 否 | 需手动发 SIGINT 的交互式中断测试 |

配方 `build()` 中编译全部 14 个并真实执行其中 4 个可自动化用例（4/14），
每个用例校验内容标记（非空输出 + 特征串），空输出或缺标记即判失败，杜绝"静默通过"。
其余 10 个在 PR 补充说明中如实声明未运行及原因。

## test_package（消费者视角，2 个二进制）

- `test_version`（10 断言）: 版本字符串 `3.11.2` 前缀 + 主/次/修订号、`RTPGetErrorString` 非空且区分、
  `RTPTime(1, 500000)` 秒/微秒/double 往返。无 socket，纯 API。
- `test_packet`（6 断言）: 手工组装 12 字节 RTP 头 + 10 字节载荷 → `RTPRawPacket` 判 RTP →
  `RTPPacket` 解析零错误、长度与数据完整 → 篡改包类型字节判非 RTP。内存语义与上游
  `testrawpacket.cpp` 同构（`new[]` 数据 + `new` 地址交由 Raw 包接管释放）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 新 CMake 配置失败 | 上游 `cmake_minimum_required(VERSION 2.8)` | `CMAKE_POLICY_VERSION_MINIMUM=3.5`（同门 jthread 1.3.3 已验证） |
| 2 | `-Werror` 下编译失败风险 | 上游对 GNU 系编译器默认加 `-Wall -Wextra -Werror`，clang 被判 GNU 系 | `JRTPLIB_WARNINGSASERRORS=OFF`，警告保留、失败关闭 |
| 3 | 线程支持开关 | `JTHREAD_ENABLED` 默认取决于 `find_package(JThread)` 是否命中 | 显式 `requires jthread/1.3.3`（透传头与库）+ 开关置 ON |
| 4 | tests/ 无 ctest 注册 | 上游测试为 14 个手动程序，`cmake.test()` 无事可做 | `JRTPLIB_COMPILE_TESTS=ON` 全编译 + 配方内直调 4 个可自动化程序并校验输出标记 |
| 5 | 库名与包名不一致 | 产物为 `libjrtp.a/.so` 而非 `libjrtplib.*` | `cpp_info.libs=["jrtp"]`，测试以 `jrtplib::jrtplib` 目标链接验证 |
| 6 | 真机 `tests/tcptest.cpp:157` 编译失败：`invalid operands to binary expression ('__bind<int &, sockaddr *, unsigned long>' and 'int')` | 该文件有 `using namespace std;`，无限定 `bind(...)` 被解析为 `std::bind`（libc++ `__bind`）而非 BSD `::bind`，clang 15 + libc++-ohos 下必现 | 新增 `patches/0001-tcptest-qualify-bsd-sockets.patch`（以官方 tarball 原始字节用 difflib 重生成准确定位，并在本机以 `git apply --check` + 全量试打验证通过），把该文件的 `socket/bind/listen/connect/accept` 全部显式 `::` 限定；`build()` 另有幂等文本回退 `_fix_tcptest_bind()` 双保险 |

## 源码修改

1 个补丁（`patches/0001-tcptest-qualify-bsd-sockets.patch`，见上表 #6）。OHOS 相关特性探测（`poll`/`clock_gettime`/
`ifaddrs`/`MSG_NOSIGNAL` 等）上游均已做编译期特性测试，缺失时自动降级，无需源码改动。

## 依赖版本

- `jthread/1.3.3`（制品仓已发布，`transitive_headers=True, transitive_libs=True`）
- OHOS 系统库 `pthread`（`package_info` 声明）
- 无其他三方依赖

## 验证结果

待 HMBS 真机预检（conan create 全链路：上游 4 程序 + test_package 2 程序）回填。
本地未运行 conan（按任务守则，W3 验证统一在真机内执行）。

## 交付物

- `include/jrtplib3/*.h`（约 60 个公开头文件）
- `lib/libjrtp.a`、`lib/libjrtp.so*`
- `lib/pkgconfig/jrtplib.pc`、`lib/cmake/JRTPLIB/JRTPLIBConfig.cmake`
- `licenses/LICENSE.MIT`
- `res/upstream_test_result.json`（上游测试机器证据：发现 14、执行 4、通过 4、跳过 10 + 逐项原因，随包发布供 test_package 复核）

## 注意事项

- 上游在非 MSVC 平台恒同时安装静态与动态库，`shared` 选项仅影响 `BUILD_SHARED_LIBS`
  透传，不改变产物集合；已在 manifest `configure_options` 如实记录。
- `testrawpacket` 需绑定本机 UDP 5000 端口并做回环收发（约 30 秒），CI/真机同源环境已覆盖；
  若未来环境收紧回环网络，回退到 3 用例并更新本文与 PR。
- 纯库包，无可执行产物，不建 `commands.json`（R38）。
