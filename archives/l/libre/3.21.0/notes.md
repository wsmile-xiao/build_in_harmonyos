# libre 3.21.0 适配笔记（HarmonyOS PC · CMake）

## 定位
- 产出共享库 `libre.so.31.21.0`（包名 `libre`，库名 `-lre`，CMake 目标 `libre::libre`）。
- 上游 = baresip/re v3.21.0，是 baresip/rem 生态的实时通信基础库（RTP/RTCP、SIP、SDP、STUN/TURN/ICE、DNS、内存池、线程）。

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-21
- 编译器: clang 15（aarch64-unknown-linux-ohos）
- CONAN_HOME: `~/tmp/ch/home-qc2-libre`
- 状态: built

## 源码
- https://github.com/baresip/re/archive/refs/tags/v3.21.0.tar.gz
- sha256: `ef4327eb46167bf91e91d2cf56214244d7c57b401f0f170a7cef7c1d65b48228`

## W0/W0b
- 依赖预检 PASS；语言预检 `lang_checked`（任务声明 cpp，源码 C，c↔cpp 兼容族）。
- 上游顶层 CMake 不调用 `find_package(OpenSSL)`，但 `test/CMakeLists.txt` 无条件把 `${OPENSSL_LIBRARIES}` 放进 `retest` 链接列表 → 交叉环境需显式声明 `openssl/3.5.8.1` 并喂 `OPENSSL_*` cache 变量。
- `USE_OPENSSL=OFF` 会在 `src/hmac/hmac_sha1.c` 触发 `#error missing HMAC-SHA1 backend`（上游 `cmake/re-config.cmake` 无条件 `find_package(OpenSSL 1.1.1)`），故置 ON。

## 上游测试账本（R51 / §10.1 五维）
- `test/test.c` 有**两张注册表**：
  - `tests[]`（单元）：**197** 项
  - `tests_integration[]`（集成/网络）：**15** 项
  - `N_static = 212`（全文件 `TEST(` 计数 213，含 `#define TEST(a)` 一行不计）
- `N_registered = 197`（`retest` 默认注册并执行的单元表；上游 `make test` 就是这个口径）
- `N_executed = 197`，其中 **1 项按平台限制逐项跳过**：`test_unixsock`（HMDFS 拒绝 `AF_UNIX bind()`，EPERM）
- 通过 **196/197**（执行项），失败 0
- 未执行 15 项 = `tests_integration[]`（需集成/网络模式的网络用例：dns/http/rtp/sipreg/tmr_jiffies/cplusplus 等），**不从分母删除**，逐项列于本文件末
- 消费者测试 `N_consumer = 22` 程序 / 245 断言（见下）

## 探索构建（真机实测，逐层剥开都有第一条真实错误）
1. G2 编译：`redefinition of 'sockaddr_storage'` —— 走 Linux 分支后 `src/net/linux/{rt,addrs}.c` 经 `<linux/netlink.h>` 拉入 `<linux/socket.h>`，与 OHOS sysroot 的 `<sys/socket.h>` 冲突（E091）。修法：`tc.extra_cflags/extra_cxxflags += "-D__MUSL__"`（仓库 41 个配方先例：acpid/adns/agetty）。
2. `retest` 从 `build/` 下运行报 `aulength.c:26 (No such file or directory [2])` —— retest 以相对路径 `./test/data` 读数据，必须 `cwd=self.source_folder`。
3. 消费者测试 `Error loading shared library libre.so.31: Permission denied` —— OHOS 动态链接器要求 `.so` 经 ELF 签名（E135）。修法：`package()` 内 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool -selfSign 1`（E077），调用签名器剔除 `LD_LIBRARY_PATH`（§12.14）。
4. test_package `env={"LD_LIBRARY_PATH": ...}` 被 conan 2.29 拒绝（`AssertionError: env argument ... should be a list`）—— 改用 `VirtualRunEnv` + `env="conanrun"`（E298）。
5. `_bindirs()` 误把 `t_*.c.obj` 当可执行文件（126）—— 过滤点号与非可执行项。
6. 22 个消费者程序此前从未真正运行过，本轮全部实跑并逐个修正断言口径（见下表）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `redefinition of 'sockaddr_storage'` | E091：linux/socket.h 与 sys/socket.h 冲突 | `-D__MUSL__`（tc.extra_cflags/extra_cxxflags） |
| 2 | retest 报 `(No such file or directory [2])` | retest 用相对路径 `./test/data` | `self.run(..., cwd=self.source_folder)` |
| 3 | 消费者 dlopen `.so` EACCES/Permission denied | E135：未签名共享库被链接器拒载 | `package()` 内 sign-elf（去 `.codesign` 段 + `-selfSign 1`，`env -u LD_LIBRARY_PATH`） |
| 4 | `env argument to ConanFile.run() should be a list` | conan 2.29 `run(env=)` 只接受脚本名/列表 | 改用 `VirtualRunEnv` + `env="conanrun"` |
| 5 | test() 去执行 `t_*.c.obj`（126） | `_bindirs()` 只按前缀匹配 | 过滤含 `.` 且非可执行的文件 |
| 6 | 22 个消费者程序 11 个失败 | 断言按臆测 API 语义书写（未初始化 re、`sa_in` 字节序、`mem_deref` 返回值、`pl_dup` 复制语义、`hash_lookup` 需 handler、`list_flush` 会 mem_deref 栈对象等） | 逐个按实现语义修正；全部 22 程序实跑通过 |

## 源码修改

| 补丁 | 内容 | 原因 |
|------|------|------|
| `patches/0001-test-unixsock-skip-ephemeral-EPERM.patch` | `test/unixsock.c`：`unixsock_listen_fd()` 返回 `EPERM` 时 `return ESKIPPED` | HMDFS 拒绝 `AF_UNIX bind()`（短/长路径均实测 EPERM），该用例无法在本平台执行；用上游自带的 `ESKIPPED` 机制逐项申报跳过，而不是让整套 retest 失败 |

## 依赖版本
- `openssl/3.5.8.1`（上游 test/ 无条件链接 `${OPENSSL_LIBRARIES}`，且 HMAC/AES/TLS 后端需要）
- 系统库：`m`、`pthread`、`dl`

## 验证结果

```bash
export PATH=$HOME/.local/bin:$PATH TMPDIR=$HOME/tmp \
       CONAN_HOME=$HOME/tmp/ch/home-qc2-libre SSL_CERT_FILE=$HOME/usr/local/ssl/cert.pem
cd ~/qzy/QC-2-libre-3.21.0
python3 scripts/ohc-run.py conan-verify libre 3.21.0
```
（结果见 `reports/conan-verify-report.md`）

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libre.so.31.21.0`（+ `.so`/`.so.31` 软链） | 共享库（aarch64/OHOS，已 ELF 签名） |
| `lib/pkgconfig/libre.pc`、`lib/cmake/libre/*` | pkg-config 与 CMake 消费入口 |
| `include/re*.h` | 上游公共头 |

## 未执行的 15 项上游集成用例（`tests_integration[]`，不从分母删除）

需集成/网络模式（上游 `retest -i` 口径）运行，非 `make test` 默认范围：

`test_dns_cache_http_integration`、`test_dns_http_integration`、`test_dns_integration`、
`test_net_dst_source_addr_get`、`test_rtp_listen`、`test_sip_drequestf_network`、
`test_sipevent_network`、`test_sipreg_tcp`、`test_sipreg_tls`、`test_sipreg_udp`、
`test_tmr_jiffies`、`test_tmr_jiffies_usec`、`test_turn_thread`、
`test_thread_cnd_timedwait`、`test_cplusplus`（共 15 项）。

## 注意事项
- 包是 shared：消费者运行时需 `LD_LIBRARY_PATH` 指向包内 `lib/`（test_package 用 `VirtualRunEnv` 的 conanrun 脚本）。
- 上游 `lib/cmake/re/` 里的 `re-config.cmake` 不是真正的 config 文件，已由 `package()` 移除；消费者统一用 conan 生成的 `libre-config.cmake`。
---

**编译结束**: 2026-09-21 08:37
**最终状态**: built
