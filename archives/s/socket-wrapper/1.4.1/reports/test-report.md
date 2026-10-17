# socket-wrapper 1.4.1 HarmonyOS 测试报告

## 测试环境

- 构建宿主：Windows x86_64
- 目标：HarmonyOS 6.0.0.48 x86_64 模拟器，Linux 5.10.210
- 原生 CI：OpenHarmonyPCDeveloper-CI-012，PR #8375，构建 #40332
- SDK：OpenHarmony SDK 26.0.0，Clang 15.0.4，兼容 API 20
- Conan：2.29.1
- 目标执行身份：`uid=2000(shell)`，SELinux `u:r:sh:s0`，Enforcing
- 测试依赖：`cmocka/2.0.2`

## 上游测试清点

1.4.1 源码的 `tests/` 目录经 `UNIT_TESTING=ON` 配置后注册 31 个 CTest 测试组。构建日志完成全部 76 个 Ninja 编译/链接步骤，包含 31 个测试可执行文件、`echo_srv`、fake UID preload helper 和 fork/thread helper。

## 构建与 Conan 结果

- 干净 `conan create`：退出 0。
- 配方修订：`socket-wrapper/1.4.1#4f3c7b2972cc9a038a7e6287f856de5f`。
- 包 ID：`98b7613297184b0d0c08c05eacfab8da3715e202`。
- 包修订：`31141eddb1c7f5750165d1635a3ae426`。
- `libsocket_wrapper.so`、版本化共享库和 noop 库完成安装与自签名。
- Conan `test_package` 完成 CMake configure、编译和链接；Windows 交叉构建宿主按 `can_run()` 跳过目标程序执行。

## HarmonyOS 原生 CI #40332

- 构建、链接、测试 ELF 签名均成功。
- CTest 注册并执行 31 个上游测试组，30 个通过，唯一失败为 `test_ioctl`。
- 失败点为 `tests/test_ioctl.c:101`：`ioctl(fd, SIOCGPGRP, &grp)` 返回 `-1`，测试预期为 `0`。
- socket-wrapper 1.5.2 的既有独立探针已证明：HarmonyOS 对普通、未使用 `LD_PRELOAD` 的 UDP socket 执行相同 ioctl 也返回 `EACCES`。该失败是平台能力限制，不是 socket-wrapper 拦截缺陷。
- 补丁 `0009-tests-CMakeLists-ohos-ioctl.patch` 保留通用测试列表中的 `test_ioctl`，仅在 CMake 检测到 `__OHOS__` 时不注册该测试。修复后的原生 CI 复跑结果待补充。

## 目标机逐项执行

31 个上游测试组及辅助 ELF 均重新自签名后部署。每项使用独立短 `TMPDIR`/`SOCKET_WRAPPER_DIR`，并预加载 fake UID helper 与 `libsocket_wrapper.so`。

| # | CTest 项 | shell 域结果 | 证据/分类 |
|---:|---|---|---|
| 1 | test_ioctl | FAIL | `ioctl` 断言失败；需在允许 AF_UNIX 的域中复核平台差异 |
| 2 | test_tcp_listen | FAIL | 两个用例均返回 `EADDRINUSE`；待目标运行域复核 |
| 3 | test_tcp_dup2 | PASS | 1/1 |
| 4 | test_fcntl | PASS | 2/2 |
| 5 | test_fcntl_lock | PASS | 1/1 |
| 6 | test_echo_tcp_connect | BLOCKED | `echo_srv` 已启动，AF_UNIX 初始化后 setup 失败 |
| 7 | test_echo_tcp_bind | BLOCKED | 同上 |
| 8 | test_echo_tcp_socket_options | BLOCKED | 同上 |
| 9 | test_echo_tcp_sendmsg_recvmsg | BLOCKED | 同上 |
| 10 | test_echo_tcp_sendmmsg_recvmmsg | BLOCKED | 同上 |
| 11 | test_echo_tcp_write_read | BLOCKED | 同上 |
| 12 | test_echo_tcp_poll | BLOCKED | 同上 |
| 13 | test_echo_tcp_writev_readv | BLOCKED | 同上 |
| 14 | test_echo_tcp_get_peer_sock_name | BLOCKED | 同上 |
| 15 | test_echo_udp_sendto_recvfrom | BLOCKED | 同上 |
| 16 | test_echo_udp_send_recv | BLOCKED | 同上 |
| 17 | test_echo_udp_sendmsg_recvmsg | BLOCKED | 同上 |
| 18 | test_swrap_unit | PASS | 1/1 |
| 19 | test_max_sockets | PASS | 当前 6.0.0.48 实例通过；与前次启动结果不同，按最新独立复测记录 |
| 20 | test_public_functions | PASS | 4/4 |
| 21 | test_close_failure | PASS | 1/1 |
| 22 | test_tcp_socket_overwrite | BLOCKED | `bind()` 返回 `EACCES` |
| 23 | test_syscall_uwrap | PASS | 1/1 |
| 24 | test_thread_sockets | PASS | 1/1 |
| 25 | test_thread_echo_tcp_connect | BLOCKED | `echo_srv` 已启动，AF_UNIX 初始化后 setup 失败 |
| 26 | test_thread_echo_tcp_write_read | BLOCKED | 同上 |
| 27 | test_thread_echo_tcp_sendmsg_recvmsg | BLOCKED | 同上 |
| 28 | test_thread_echo_udp_send_recv | BLOCKED | 同上 |
| 29 | test_sendmsg_recvmsg_fd | FAIL | SCM_RIGHTS 路径返回 -1；待目标运行域复核 |
| 30 | test_echo_tcp_sendmsg_recvmsg_fd | TIMEOUT | 17 个 setup 连续受阻，8 秒逐项保护超时 |
| 31 | test_fork_thread_deadlock | PASS | 1/1 |

普通 HDC shell 域的最新观测计数为 10 PASS、20 FAIL、1 TIMEOUT。该数字只描述受限执行域，不能作为最终 HarmonyOS 兼容通过率。

## 环境阻塞证据

- 消费者程序成功加载 `libsocket_wrapper.so` 并将 `127.0.0.1:21777` 映射为 `/data/local/tmp/.../T015511`，随后 AF_UNIX `bind()` 返回 `errno=13 (Permission denied)`。
- 不使用 `LD_PRELOAD` 的最小 AF_UNIX 探针在同一 `/data/local/tmp` 文件系统也稳定返回 `EACCES`，而普通文件创建成功，定位到 HDC shell SELinux 域而非 wrapper 逻辑。
- 模拟器没有 `/data/storage/el2/base/temp`，也没有可直接使用的调试应用沙箱。
- 用户明确授权后执行 `hdc smode`，公开镜像返回 `Cannot set root run mode in undebuggable version`；设备始终保持 `uid=2000(shell)`、`u:r:sh:s0`、SELinux Enforcing，无需恢复权限。
- 消费者负向控制（无 `LD_PRELOAD`）在 `socket_wrapper_enabled()` 检查处失败；恢复预加载后越过该检查，并在重定向的 AF_UNIX `bind()` 处返回 `EACCES`。

## 回显服务路径回归验证

交叉构建最初把 Windows `BINARYDIR` 固化进目标 ELF，回显类测试在目标机报告宿主绝对路径不可访问。补丁增加 `SOCKET_WRAPPER_ECHO_SERVER` 覆盖后：

- 无效覆盖 `/does/not/exist`：稳定出现 `not found`（RED/反向验证）。
- 有效覆盖 `./echo_srv`：不再出现宿主路径或 `not found`，目标端 helper 启动并进入后续 socket setup（GREEN 到环境边界）。

## 待完成验证

需要由 HarmonyOS 原生 CI 重新运行 OHOS 适用的 30 个上游测试组及 Conan 消费者测试。应用沙箱或可调试模拟器仍可用于补充复核普通 HDC shell 域受 SELinux 阻塞的路径。
