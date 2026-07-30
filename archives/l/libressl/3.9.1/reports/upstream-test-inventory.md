# LibreSSL 3.9.1 上游测试清单与路径 B 说明

## 清单口径

- 精确版本：LibreSSL 3.9.1。
- 清单命令：`cmake -DLIBRESSL_TESTS=ON -DENABLE_EXTRATESTS=ON ...` 后执行
  `ctest -N`。
- 清单结果：128 个已注册 CTest 用例。
- 上游 `tests/CMakeLists.txt` 中被注释的 `dtlstest` 没有随 3.9.1 源码包
  提供对应源文件，也没有注册为 CTest 用例，因此不属于该版本的可执行测试清单。

完整的 128 项清单如下：

```text
aes_test, aes_wrap, aeadtest, arc4randomforktest, asn1api, asn1basic,
apitest, asn1complex, asn1evp, asn1object, asn1oct, asn1test,
asn1string_copy, asn1time, asn1x509, asn1_string_to_utf8, base64test,
bio_asn1, bio_chain, bf_test, bio_dump, bio_host, bn_add_sub, bn_cmp,
bn_convert, bn_gcd, bn_isqrt, bio_mem, bn_mod_inverse, bn_mod_sqrt,
bn_mont, bn_mod_exp, bn_print, bn_shift, bn_test, bn_to_string,
bn_primes, bn_word, buffertest, bytestringtest, casttest, chachatest,
cipher_list, cipherstest, clienttest, cmstest, configtest, constraints,
cttest, destest, dhtest, dsatest, ecc_cdh, ec_asn1_test,
ec_point_conversion, ecdhtest, ecdsatest, ectest, ed25519test,
evp_ecx_test, evp_pkey_check, evp_pkey_cleanup, evptest, evp_test,
exdata_test, explicit_bzero, exportertest, freenull, gcm128test,
handshake_table, hkdf_test, hmactest, ideatest, igetest, key_schedule,
keypairtest, md_test, objectstest, ocsptest, optionstest, pbkdf2,
pidwraptest, pkcs7test, poly1305test, policy, pq_test, quictest,
randtest, rc2_test, rc4_test, recordtest, record_layer_test, rfc3779,
rfc5280time, rmd_test, rsa_test, servertest, sha_test, shutdowntest,
signertest, sm3test, sm4test, ssl_get_shared_ciphers, ssl_methods,
ssl_set_alpn_protos, ssl_verify_param, ssl_versions, ssltest, testdsa,
testenc, testrsa, timingsafe, tlsexttest, tlslegacytest, tlstest,
tls_ext_alpn, tls_prf, bn_unit, valid_handshakes_terminate, verifytest,
x25519test, x509attribute, x509_algor, x509_asn1, x509_info, x509name,
x509req_ext, utf8test
```

## 原始结果与根因

在 Linux/glibc 构建中启用全部额外测试后，第一次完整尝试不能形成合格结果：

1. `ocsptest` 的第二个目标 `cloudflare.com` 没有返回测试所需的 OCSP
   响应，因此失败。
2. `pidwraptest` 通过不断派生进程等待内核 PID 自然回绕，运行超过 10
   分钟仍未结束；这是无确定上界的环境依赖测试。
3. 处理上述两项后，第二次结果为 127/128；`bio_host` 仍失败。glibc
   `getaddrinfo()` 接受简写/十六进制 IPv4、空服务名及溢出的数值端口，
   而 OpenBSD 的严格解析语义拒绝这些输入。

## 最小修复与未弱化证明

- `ocsptest` 仍执行两个真实的公网 TLS/OCSP 交互，仅将不能提供所需 OCSP
  响应的目标替换为可提供 OCSP 响应的 `www.amazon.co.uk`，并增加 30 秒
  有界超时。
- `pidwraptest` 仍验证“PID 被复用时，父子进程 PRNG 输出不得相同”的原始
  安全性质；通过链接器 `--wrap=getpid` 确定性模拟 PID 复用，若两条随机
  流相同仍会失败，并增加 30 秒有界超时。
- `bio_host` 的上游测试文件和全部断言保持不变。兼容补丁在生产实现中对
  数字 IPv4 和数字端口做严格范围/格式校验，拒绝模糊地址、空服务名和
  `65536` 以上的溢出值，属于行为收紧而不是放宽测试。

## 修复后结果

Release 与 Debug 均使用相同完整清单：

```text
Upstream inventory: 128 cases (basis: CTest entries with ENABLE_EXTRATESTS=ON)
Executed: 128
Passed: 128
Failed: 0
Skipped/not applicable: 0
Pass rate: 128/128 (100%)
```

三个受影响用例在两种构建类型中均实际执行并通过：
`bio_host`、`ocsptest`、`pidwraptest`。
