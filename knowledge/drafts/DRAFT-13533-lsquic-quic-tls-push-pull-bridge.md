# DRAFT-13533：BoringSSL 推模式 QUIC TLS API → OpenSSL 3.5+ 拉模式桥接

## 适用场景
任何按 BoringSSL QUIC TLS API 编写的 QUIC 协议库（lsquic 及同族）要链接
制品仓 OpenSSL 3.5+ 时。与 msquic（自带 OpenSSL 适配层）不同，lsquic
4.9.4 源码层从未迁移 OpenSSL——CMakeLists 有检测分支（探测
SSL_set_quic_tls_cbs）但源码零 HAVE_OPENSSL 分支，master 同样。

## 报错签名（命中任一即适用）
```
fatal error: 'openssl/aead.h' file not found
fatal error: 'openssl/chacha.h' file not found
fatal error: 'openssl/hkdf.h' file not found
unknown type name 'EVP_AEAD_CTX'
use of undeclared identifier 'SSL_provide_quic_data'
use of undeclared identifier 'SSL_set_quic_method'
variable has incomplete type 'EVP_CIPHER_CTX'
undefined symbol: HKDF_expand
```

## 根因
| 维度 | BoringSSL（上游写法） | OpenSSL 3.5+（仓内） |
|---|---|---|
| 数据流 | 推：`SSL_provide_quic_data(ssl, level, buf, len)` | 拉：`crypto_recv_rcd` 回调取窗口 + `crypto_release_rcd` 报消耗 |
| 应用回调 | `SSL_set_quic_method` + `SSL_QUIC_METHOD`（5 回调，带 level） | `SSL_set_quic_tls_cbs` + `OSSL_DISPATCH`（6 回调，send/alert 不带 level） |
| 密钥下发 | set_read/write_secret(cipher 一并传) | `yield_secret(prot_level, direction)`（cipher 要自己 SSL_get_current_cipher） |
| 传输参数 | `SSL_set/get_quic_transport_params` | 发送 `SSL_set_quic_tls_transport_params`；接收 `got_transport_params` 回调 |
| AEAD | EVP_AEAD_CTX_seal/open + EVP_CIPHER_CTX 值语义内嵌 | EVP_CIPHER_CTX 不透明（必须堆句柄）+ enc/dec 分离 |
| HKDF | 独立 HKDF_extract/HKDF_expand 函数 | 仅 EVP_PKEY_HKDF pkey 路径 |

## 修法（四要素 compat shim）
1. **推拉翻转**：`SSL_provide_quic_data` 存 per-SSL rcd 队列（SSL ex_data
   持有 bridge 结构）；recv_rcd 交出整个未读窗口，release_rcd 按消耗量
   memmove 回退未消费尾部
2. **回调转发**：OSSL_DISPATCH 六回调 → 原 SSL_QUIC_METHOD 五回调；
   level 映射 OSSLRECORD_PROTECTION_LEVEL_* ↔ ssl_encryption_level_t
   （值 0-3 恰好对齐）；send/alert 的 level 用最近 yield_secret 跟踪
3. **EVP_AEAD 重实现**：seal/open 在 EVP_CIPHER 上 one-shot 封装；GCM
   每次调用按实际 nonce_len 重设 IVLEN（8-16 可变）；tag_len 从
   EVP_AEAD_CTX_init 传入并存 ctx（8-16 可变——gQUIC STK 用 12、QUIC
   用 16，忽略该参数会烧掉 test_dec/test_stk）；ChaCha20-Poly1305 固定
   12 IV
4. **散件**：HKDF_extract=HMAC 一次；HKDF_expand=EVP_PKEY_HKDF 的
   EXPAND_ONLY 模式；CRYPTO_chacha_20=EVP_chacha20（16 字节
   IV=counter||nonce 小端拼装）；SSL_SESSION_to/from_bytes=
   i2d/d2i_SSL_SESSION（同 DER）

## 0-RTT 语义降级（如实申报）
BoringSSL 的 `SSL_in_early_data`/`SSL_reset_early_data_reject`/
`SSL_set_quic_early_data_context`/`SSL_CTX_set_early_data_enabled` 无
拉模式等价物（OpenSSL 的 SSL_read_early_data 系是应用层 TLS 完全不同
模型）。桥接后：**会话恢复正常工作，0-RTT 早数据不发送**。握手/1-RTT/
密钥更新全功能。

## CMake 探测的坑
上游 `check_symbol_exists(SSL_set_quic_tls_cbs ...)` 需要完整编译+链接
目标 TLS 库——交叉环境 check 无法链接主机 openssl → 探测必失败。
对策：`LSQUIC_LIBSSL=OPENSSL`（上游提供的强制开关）跳过探测直接定义
HAVE_OPENSSL。

## 验证
- conan create + test_package PASS（引擎创建即走 OSSL_DISPATCH 注册路径）
- 上游 82 测试：80 过 + dec/stk（tag_len 可变修复后）+ 1 平台豁免
