# openssl 3.5.7 真机测试报告

- 设备：HarmonyOS PC aarch64（8 逻辑核），OHOS SDK 26.0.0.18 / clang 15.0.4，profile `ohos-aarch64`
- 命令：`conan create archives/o/openssl/3.5.7 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
- 源码：官方 tag `openssl-3.5.7`，SHA-256 `a8c0d28a529ca480f9f36cf5792e2cd21984552a3c8e4aa11a24aa31aeac98e8`
  （与 openssl.org 发布的同名 `.sha256` 文件逐字符一致）

## 三轮实跑

| 轮次 | 时间 | build() 内的上游步骤 | harness 结果 | 退出码 |
|---|---|---|---|---|
| 1 | 13:31:29 → 14:01:30（30 min 01 s） | 全量 `make test` | `Files=344, Tests=4024, 930 s, Result: PASS` | `CREATE_EXIT:0` |
| 2 | 15:25:07 → 16:00:47（35 min 40 s） | 全量 `make test`（含 T9 断言修正后的 test_package） | `Files=344, Tests=4024, 1144 s, Result: PASS` | `CREATE_EXIT:0` |
| 3 | 16:40:26 → 17:09:28（29 min 02 s） | **最终配方**：`timeout 1500 make test TESTS="<116 脚本>"` | `Files=116, Tests=3086, 736 s, Result: PASS` | `CREATE_EXIT:0` |

另有一次清单单独计时（同 116 脚本）：16:15:24 → 16:26:34，`Files=116, Tests=3085, 665 s`，`RC:0`。

第 3 轮是**当前分支上那份配方**的完整验证：`conan create` 退出码 0、`not ok` 0 条、
116 个 `.t` 全部 ok、消费者 `=== Results: 12/12 tests passed ===`。
第 1、2 轮证明上游全量套件在鸿蒙上可 100% 通过（4024 用例），CI 内改跑 116 脚本清单的
原因见 `../notes.md`（单包 3600 s 预算 + 全量 harness 就要 930～1144 s）。

## 阶段耗时（第 1 轮）

| 阶段 | 结束时刻 | 说明 |
|---|---|---|
| `perl ./Configure ... no-asm no-shared --with-rand-seed=getrandom` | 13:31 | `Configuring OpenSSL version 3.5.7 for target linux-aarch64` |
| `make build_sw -j2` | 13:45:25 | libssl.a 13:43:16 / libcrypto.a 13:43:31 / apps/openssl 13:45:25 |
| 上游测试程序 | ≈13:46 | `make test` 自带 `build_programs`，248 个 C 测试程序 |
| `make test` | 14:01 | 930 wallclock secs |


## 上游 `make test` 结果（全量，未裁剪清单、未吞失败）

```
Using HARNESS_JOBS=4
...
Files=344, Tests=4024, 930 wallclock secs (23.29 usr 10.98 sys + 149.53 cusr 122.17 csys = 305.97 CPU)
Result: PASS
```

- `not ok` 计数：**0**
- `test/recipes/*.t` 共 345：48 个 skipped（下表逐条）+ 297 个 ok，48 + 297 = 345
- 另有一次 `Files=1 / Result: NOTESTS`，对应 `00-prep_fipsmodule_cnf.t`（FIPS 构建预备脚本，本身不含用例）
- 抽样确认真跑并 ok 的代表性脚本：`80-test_ssl_new.t`、`90-test_sslapi.t`、`80-test_dtls_mtu.t`、
  `30-test_evp_pkey_provided.t`、`90-test_store.t`、`80-test_cmp_http.t`、`99-test_ecstress.t`

### 48 个 skipped 明细（原因由上游 `skip()` 按构建配置给出，非本地禁用）

| # | 脚本 | 上游给出的原因 |
|---|---|---|
| 1 | 00-prep_fipsmodule_cnf.t | FIPS module config file only supported in a fips build |
| 2 | 01-test_fipsmodule_cnf.t | Test only supported in a fips build |
| 3 | 03-test_fipsinstall.t | Test only supported in a fips build |
| 4 | 20-test_cli_fips.t | Test only supported in a fips build with security checks |
| 5 | 30-test_pairwise_fail.t | These tests are unsupported in a non fips build |
| 6 | 90-test_fipsload.t | Test is disabled with disabled fips |
| 7 | 02-test_windows_registry.t | Windows registry tests are only available on windows |
| 8 | 04-test_bio_tfo.t | This test requires enable-tfo |
| 9 | 82-test_tfo_cli.t | test_tfo_cli needs tfo enabled |
| 10 | 05-test_rc5.t | rc5 is not supported by this OpenSSL build |
| 11 | 07-test_bio_comp.t | No compression algorithms |
| 12 | 90-test_cert_comp.t | Certificate compression is disabled in this OpenSSL build |
| 13 | 30-test_acvp.t | ACVP is not supported by this test |
| 14 | 70-test_sslkeylogfile.t | test_sslkeylogfile requires SSLKEYLOGFILE support |
| 15 | 90-test_shlibload.t | Test only supported in a shared build |
| 16 | 90-test_tls13secrets.t | test_tls13secrets is not supported in this build |
| 17 | 95-test_external_cf_quiche.t | No external tests in this configuration |
| 18 | 95-test_external_gost_engine.t | No external tests in this configuration |
| 19 | 95-test_external_krb5.t | No external tests in this configuration |
| 20 | 95-test_external_oqsprovider.t | No external tests in this configuration |
| 21 | 95-test_external_pkcs11_provider.t | No external tests in this configuration |
| 22 | 95-test_external_pyca.t | No external tests in this configuration |
| 23 | 95-test_external_tlsfuzzer.t | No external tests in this configuration |
| 24-48 | 70-test_certtypeext.t, 70-test_comp.t, 70-test_key_share.t, 70-test_npn.t, 70-test_renegotiation.t, 70-test_sslcbcpadding.t, 70-test_sslcertstatus.t, 70-test_sslextension.t, 70-test_sslmessages.t, 70-test_sslrecords.t, 70-test_sslsessiontick.t, 70-test_sslsigalgs.t, 70-test_sslsignature.t, 70-test_sslskewith0p.t, 70-test_sslversions.t, 70-test_sslvertol.t, 70-test_tls13alerts.t, 70-test_tls13certcomp.t, 70-test_tls13cookie.t, 70-test_tls13downgrade.t, 70-test_tls13hrr.t, 70-test_tls13kexmodes.t, 70-test_tls13messages.t, 70-test_tls13psk.t, 70-test_tlsextms.t | needs the dynamic engine feature enabled（dynamic engine 依赖可动态加载的引擎；本包按 R26 以 `no-shared` 构建，避免 libssl/libcrypto 与系统 `/lib` 同名污染。这批脚本是同一 TLS 报文探测机制，握手与算法主覆盖由实跑并通过的 80-test_ssl_new / 90-test_sslapi / 80-test_dtls_mtu / 30-test_evp_pkey_provided 等承担） |

取数命令（日志文件上执行）：

```sh
grep -oE "^[0-9]+-[A-Za-z0-9_.-]+\.t \.+ skipped: .*" create.log | sort -u | wc -l   # 48
grep -cE "\.t \.+ ok$" create.log                                                   # 297
grep -cE "not ok" create.log                                                        # 0
```

## 消费者（L1 test_package，鸿蒙特有）结果

```
=== Results: 12/12 tests passed ===
OpenSSL version: OpenSSL 3.5.7  9 Jun 2026
```

T1 版本探测 / T2 SHA-2 族 + SHA-256 KAT / T3 MD5+SHA1 legacy / T4 HMAC-SHA256（RFC 4231 KAT）/
T5 AES-256-CBC / T6 AES-256-GCM（SET_TAG + 明文回读）/ T7 RSA-2048 OAEP / T8 EC P-256 签名验签（含篡改拒绝）/
T9 RAND_bytes 熵 / T10 错误队列 / T11 TLS 1.3 上下文 / T12 X.509 自签证书签发+验签，全部 `[PASS]`。

编译期仅 `MD5`/`RSA_*`/`EC_KEY_*` 的 `-Wdeprecated-declarations` 提示（OpenSSL 3.x 有意把 legacy
算法迁到 provider，测试正是为验证这些旧路径仍可用而显式调用），无错误。
