# boringssl 0.20260927 — 测试报告（R51 + R34 + R53）

- 包：`boringssl/0.20260927`（官方 main 快照 `e98a6564`，2026-09-25）
- 平台：HarmonyOS PC（aarch64，musl，OHOS 6.0）
- 编译器：clang 15.0.4（`/data/service/hnp/bin/clang`），Release
- 日期：2026-09-28

## R51 上游测试三步法

### ① 清点
BoringSSL 上游无 ctest/pytest 注册；测试为 gtest 独立二进制（`BUILD_TESTING=ON`
默认构建但不安装），另有两个 Go 驱动套件（`ssl/test/runner`、
`util/all_tests.go`）与 fuzz 目标（需 `-DFUZZ=1`）。

### ② 实跑（真机，非交叉模拟）

命令（cwd = 源码根；`--gtest_filter=-*DeathTest*` 见下方平台说明）：

```sh
cd boringssl-0.20260927.work
TEST_TMPDIR=$HOME/tmp/gtest <build>/crypto_test --gtest_filter=-*DeathTest*
TEST_TMPDIR=$HOME/tmp/gtest <build>/ssl_test    --gtest_filter=-*DeathTest*
<build>/decrepit_test
<build>/pki_test
<build>/urandom_test
```

| 二进制 | rc | 通过 / 执行 | 耗时 | 说明 |
|--------|----|-------------|------|------|
| crypto_test | 0 | **1844 / 1845** | 76.1s | 1 上游自带 skip（`AEADTest.WycheproofAESEAX`）；4 个 disabled；排除 4 个 DeathTest |
| ssl_test | 0 | **484 / 484** | 2.9s | 排除 2 个 DeathTest |
| decrepit_test | 0 | **12 / 12** | 0.01s | — |
| pki_test | 0 | **1332 / 1332** | 1.8s | — |
| urandom_test | 1 | **0 / 1** | 0.1s | `PTRACE_TRACEME: Permission denied`（平台拒绝 ptrace） |
| **合计** | | **3672 / 3676** | ~81s | 通过率 **99.9%** |

平台排除的 6 个 DeathTest（crypto 4：CBB/Array/Vector/InplaceVector；
ssl 2：SpanDeathTest）：gtest `CapturedStream` 在非 Android/iOS 分支硬编码
`/tmp/gtest_captured_stream.XXXXXX`（`gtest-port.cc:1104`，TEST_TMPDIR 不生效），
鸿蒙 `/tmp` 只读（E002）→ 用例在写临时文件时 abort，运行时过滤。

### ③ 结论
- 唯一失败为 `urandom_test`（白盒 syscall 拦截依赖 ptrace），**平台限制非库缺陷**；
  熵源功能由 `RAND_bytes` 相关用例 + test_package E2E 覆盖。
- recipe `build()` 内已集成 crypto_test + ssl_test 实跑（blocking，`timeout 1800`），
  与 CI L1c 口径一致。
- Go 套件不适用：平台无 Go 工具链；R47 已按边界规则判定项目语言为 cpp
  （rust/ 为可选绑定、go 为辅助工具，详见 notes.md）。

## R34 消费者测试（test_package/test_boringssl.cc）

27 断言全通过（`ctest -R boringssl_consumer_e2e`，输出 `R34_RESULT=PASS`）：

- 内存 BIO pair 上完整 **TLS 1.3 握手**（服务端自签名证书、客户端
  `SSL_VERIFY_PEER` + `X509_STORE_add_cert` 校验、协商密码套件、
  `SSL_get_peer_certificate` 拿到证书）+ 双向应用数据收发各 1 轮
- BIGNUM：`12345678901234567890 + 98765432109876543210 = 111111111011111111100`
- SHA-256("abc") 已知向量
- `RAND_bytes` 非零输出

## R53 鸿蒙特有测试（test_package/ohos_specific_test.py，23 断言全过）

- R26 静态交付：`libssl.a` / `libcrypto.a` 存在；**包内 0 个 .so**
- `bssl` 元数据：ELF64 / e_machine=AArch64 / PIE / 解释器
  `/lib/ld-musl-aarch64.so.1` / 无 RPATH / NEEDED 不含 libssl·libcrypto
- 安全加固：GNU_RELRO + BIND_NOW（full RELRO）、GNU_STACK 非可执行（NX）
- **真机实跑**：`bssl sha256sum` 输出与 Python hashlib 已知向量一致（rc=0）；
  `bssl rand 16` 返回 16 字节随机数（rc=0，熵源路径）；注：`bssl --help`
  退出码为 1（Usage 输出到 stdout），CI L2 仅 warn 非阻塞
- 静态库符号：`libcrypto.a` 含 `BN_mod_exp`、`libssl.a` 含 `SSL_CTX_new`
- 头文件交付：`openssl/{ssl,crypto,evp,bn}.h`

## 汇总

| 层级 | 结果 |
|------|------|
| conan-verify | **PASS**（G0/G1/G2/G3；G4/L2/L4/L5 因框架包 ID 解析偏差跳过，R53 等价核验） |
| 上游 gtest（R51，conan create 内 build() 实跑） | crypto 1844/1845 + ssl 484/484；真机扩展 3672/3676（99.9%） |
| R34 消费者 E2E | 27 / 27（ctest 1/1 Passed） |
| R53 鸿蒙特有 | 23 / 23 |
| 合计断言 | 3722 通过（+4 个上游 disabled 不计） |

> 证据：`reports/conan-create.log`（conan create 全量日志，GitHub 忽略的本地归档件）
> - 行 776-5210：build() 内 crypto_test（1845 用例，1844 PASS）
> - 行 5219-6349：build() 内 ssl_test（484 用例，484 PASS）
> - 行 6552-6557：test_package ctest 1/1 Passed
> - 行 6584-6585：R53 ALL OHOS SPECIFIC TESTS PASSED (23/23)
