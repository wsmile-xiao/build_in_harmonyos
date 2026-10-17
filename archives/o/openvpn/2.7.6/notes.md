# openvpn 2.7.6 适配笔记

## 编译环境
- 构建系统: autotools（release tarball 自带 configure）
- 编译日期: 2026-09-13
- 编译器: clang/clang++ 15（OHOS SDK）
- 状态: built

## 编译步骤
1. conan create，profile ohos-aarch64，triplet 显式传 --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos
2. PkgConfigDeps 生成 + PKG_CONFIG_PATH 聚合注入（openvpn configure 用 pkg-config 探测全部依赖，libcap-ng 不喂 pc 路径探测即挂）
3. make -j1（E074），make check -j1（上游系统测试）+ 逐个真实执行 17 个单元 testdriver

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: libcap-ng package not found | 依赖探测全走 pkg-config，conan 依赖 .pc 路径未注入 | conanfile generate() 里 PkgConfigDeps + 依赖 libdirs/builddirs prepend 进 PKG_CONFIG_PATH |
| 2 | networking_sitnl.c: redefinition of sockaddr_storage | E119/E091: OHOS musl sysroot linux/socket.h（linux/netlink.h 间接引入）与 sys/socket.h 重复定义 | 0001 补丁：include 前预定义 _UAPI_LINUX_SOCKET_H guard + __kernel_sa_family_t typedef |
| 3 | route.c 等所有 netlink 消费 TU 同样报错 | syshead.h 是 openvpn 全局头，逐文件修不完 | 0002 补丁：syshead.h sys/socket.h 后全局 guard（特性级修法，无平台宏） |
| 4 | config.status 无法写临时目录 | E114: configure umask 077 + HMDFS setgid → drwx--S--- | 去掉 configure 中两处 umask 077 前缀 |
| 5 | make 并行随机 EPERM | E074: HMDFS jobserver fifo | make -j1 |
| 6 | test_package 隧道项 Unrecognized option allow-compat-no-tls | openvpn 2.7.6 实际 compat 选项名不同 | 改 allow-deprecated-insecure-static-crypto（二进制 strings 实测确认）；顺带修 cipher/ping-exit（见下） |
| 9 | CI L0 门禁 no_test_sources stub_test_method | L0c 要求 test_package 有测试源码文件、L0d 要求 test() 用 self.run() | 测试逻辑重构进 test_package/test_openvpn.sh，conanfile test() 经 self.run() 驱动（本地第 10 轮全绿） |
| 7 | 隧道项 Cipher BF-CBC not supported | 静态密钥模式默认 cipher BF-CBC，OpenSSL 3.5.6 已移除 Blowfish | 配置加 cipher AES-256-CBC + auth SHA256 |
| 8 | 隧道项超时不退出 | ping-restart 是软重启循环永不退出 | 改 ping-exit 4（不活动 4s 硬退出 exit 0） |
| 10 | 上游单元测试被 configure 禁用（cmocka.pc not found） | cmocka 是 tool_requires（build context），PkgConfigDeps 默认不生成 build context .pc | PkgConfigDeps.build_context_activated=["cmocka"] + build 依赖 pc 目录注入 PKG_CONFIG_PATH；cmocka/2.0.2 已在 ohpcd 发布（OHOS armv8/clang15 二进制） |
| 11 | 单元测试 TESTS 被 !CROSS_COMPILING 门控不执行 | 上游 Makefile.am `if !CROSS_COMPILING`（configure --host 设置即 cross） | check_PROGRAMS 照常构建；conanfile _run_unit_tests() 逐个真实执行 17 个 testdriver（OHOS arm64 二进制本机原生跑），失败即 fail build |
| 12 | misc/user_pass 测试失败 test_common.h:92 assert_non_null(srcdir) | 测试经 openvpn_test_get_srcdir_dir 读源码目录数据文件（COPYRIGHT.GPL、input/*.txt），需 $srcdir | _run_unit_tests() 设 srcdir=<source>/tests/unit_tests/openvpn |
| 13 | ssl_testdriver GROUP SETUP 失败 + tls_crypt 1/18 失败：Could not create temporary file '/tmp/openvpn_cert_*.tmp' | test_ssl.c:119 get_tmp_dir()/test_tls_crypt.c:723 硬编码 /tmp；OHOS /tmp 为 erofs 只读挂载（mount: /dev/block/dm-0 on /tmp ro），无 root 无法 bind-mount | 不改上游测试源码，build() 内编译 LD_PRELOAD shim（open/fopen/stat/unlink 重定向 /tmp→$OVPN_REDIR_TMP 可写目录）作测试 harness；shim 后 ssl 17 PASS+1 SKIP（bf_cbc 上游对 OpenSSL 3.x 的已知跳过）、tls_crypt 18/18 PASS |

## 源码修改
- patches/0001-ohos-sockaddr-storage-clash.patch: networking_sitnl.c sockaddr_storage 冲突 guard
- patches/0002-syshead-socket-guard.patch: syshead.h 全局 guard（route.c 等全部 netlink 消费 TU）

## 依赖版本
- openssl/3.5.6、lzo/2.10、lz4/1.10.0、libcap-ng/0.8.5（全部静态链接进 openvpn 二进制）
- cmocka/2.0.2（tool_requires，仅上游单元测试链接用，不进运行时依赖）

## 验证结果

### 上游 22 个测试逐个真实执行（2026-09-13，本机 OHOS arm64 原生）

系统测试（tests/，5 个）——`make check` + 手动逐个执行：

| 测试 | 结果 | 证据 |
|------|------|------|
| t_lpback.sh | **PASS** (exit 0) | "tests passed: 67 failed: 0"（67 个加密回环子断言） |
| t_cltsrv.sh | **PASS** (exit 0) | 真实回环 TLS 隧道（loopback-server/client，reneg-sec 10 完整协商） |
| t_net.sh | SKIP (exit 77) | "this test runs only on Linux. SKIPPING TEST."（uname=HarmonyOS，上游硬门） |
| t_client.sh | SKIP (exit 77) | 无 t_client.rc（需真实远端 VPN 服务器）→ 提供 rc 后 "fping is not available in $PATH" → "this test must run be as root, or RUN_SUDO"（sudo -n: init challenge failed） |
| t_server_null.sh | SKIP (exit 77) | 无 t_server_null.rc → 提供 rc 后 "this test must run be as root, or RUN_SUDO"；SERVER_BASE_OPTS 需 --dev tun，实测 openvpn 报 "Cannot open TUN/TAP dev /dev/net/tun: Permission denied (errno=13)" |

单元测试（tests/unit_tests/openvpn，17 个）——cmocka/2.0.2 接入后逐个真实执行（srcdir + /tmp 重定向 shim 环境）：

| 测试 | 结果 | 子测试 |
|------|------|--------|
| argv_testdriver | **PASS** (rc=0) | 14/14 |
| auth_token_testdriver | **PASS** (rc=0) | 10/10 |
| buffer_testdriver | **PASS** (rc=0) | 19/19 |
| crypto_testdriver | **PASS** (rc=0) | 19/19 |
| dhcp_testdriver | **PASS** (rc=0) | 1/1 |
| ncp_testdriver | **PASS** (rc=0) | 6/6 |
| mbuf_testdriver | **PASS** (rc=0) | 2/2 |
| misc_testdriver | **PASS** (rc=0) | 6/6（含 test_list 读 COPYRIGHT.GPL 词频 hash） |
| options_parse_testdriver | **PASS** (rc=0) | 2/2 |
| packet_id_testdriver | **PASS** (rc=0) | 9/9 |
| pkt_testdriver | **PASS** (rc=0) | 11/11 |
| provider_testdriver | **PASS** (rc=0) | 3/3 |
| push_update_msg_testdriver | **PASS** (rc=0) | 24/24 |
| socket_testdriver | **PASS** (rc=0) | 1/1 |
| ssl_testdriver | **PASS** (rc=0) | 17 PASS + 1 SKIP（test_data_channel_roundtrip_bf_cbc：OpenSSL 3.5.6 无 Blowfish，上游条件跳过） |
| user_pass_testdriver | **PASS** (rc=0) | 10/10 |
| tls_crypt_testdriver | **PASS** (rc=0) | 18/18 |

合计：**19/22 真实执行且通过**（2 系统 + 17 单元），3 个系统测试 SKIP 原因逐项实证如上（t_net 上游仅 Linux；t_client/t_server_null 需 root 权限 + 真实网络拓扑/远端 VPN 服务器 + /dev/net/tun，OHOS 用户环境均不可得——sudo 非交互失败、tun Permission denied 已实测）。

```bash
# 主包构建：Package 'b89b128d3304547c8a52fdd4729215ee28ebe810' created（cmocka 接入后全绿）
# make check（系统测试）: TOTAL 5 / PASS 2 / SKIP 3 / FAIL 0
# 单元测试逐个执行：17/17 PASS（conan create 日志 "openvpn unit tests: argv_testdriver:PASS(rc=0); ... tls_crypt_testdriver:PASS(rc=0)"）
# conan create test_package（test_openvpn.sh via self.run()）6 项全过：
#   ok: version/platform/feature marks
#   ok: --show-ciphers (75 entries)
#   ok: --show-digests (35 entries)
#   ok: --show-tls (36 entries)
#   ok: --genkey secret
#   ok: static-key dev-null tunnel ran
```

## 注意事项
- 单元测试依赖 cmocka/2.0.2（tool_requires，ohpcd 已发布 OHOS armv8/clang15 二进制）；configure 探测经 PkgConfigDeps.build_context_activated 注入
- 上游以 CROSS_COMPILING 门控单元测试 TESTS 执行（交叉构建不自动跑）——OHOS arm64 二进制本机原生可跑，conanfile _run_unit_tests() 逐个真实执行并 fail build
- /tmp 只读（E002）对上游测试的影响与处理：test_ssl.c/test_tls_crypt.c 硬编码 /tmp 临时文件——用 LD_PRELOAD shim 重定向（不修改上游测试源码）；t_client.sh/t_server_null.sh 的 root/tun 需求不可绕过（SKIP 实证）
- openvpn 2.7.6 TLS-less 静态密钥是弃用路径（2.8 将移除），test_package 用 allow-deprecated-insecure-static-crypto 做数据通道冒烟
- 二进制为静态链接（NEEDED 仅 libc.so），无需 LD_LIBRARY_PATH
