# DRAFT-14402：quictls 3.3.x QUIC-TLS 双 API 互斥选型

## 适用场景
适配 quictls fork（OpenSSL + QUIC-TLS 扩展）到 OHOS 时需要决定 QUIC 特性组合；
或下游（msquic/lsquic 等外部 QUIC 栈）要链接制品仓 quictls 时确认 API 形态。
与 DRAFT-13533 双轨互补：彼管 consumer 侧桥接，本条目管 provider 侧特性选型。

## 报错签名（命中任一即适用）
```
boring-quic-api and quic are incompatible options
quic handshake layer error, error code 1 (0x1) ("internal error")
Connection close reason: internal error
failed in script "dyn script 0" at op 5, thread -1
70-test_quic_tserver.t / 70-test_quic_multistream.t 失败
ossl_quic_tls_tick:quic handshake layer error:ssl/quic/quic_tls.c:768
```

## 根因
quictls 3.3.0-quic1（仓库 2025-04-10 归档，后继 quictls/quictls）有两套**互斥**
QUIC-TLS API（Configure L1221 die 硬闸）：

| 特性 | 默认 | API 形态 | 消费方 |
|---|---|---|---|
| boring-quic-api | 启用 | BoringSSL 兼容推模式（SSL_set_quic_method 4 回调 / SSL_provide_quic_data / transport params） | msquic、lsquic 等外部 QUIC 栈 |
| quic（原生栈） | 禁用 | OSSL_QUIC_client_method + 内建 transport | 用 OpenSSL 内建 QUIC 栈的应用 |

原生栈在 3.3.0-quic1 有确定性上游缺陷：tserver/multistream 两套测试在
quic_tls.c:768 `ossl_tls_add_custom_ext_intern`（quic_transport_parameters
扩展注册）失败 → `RAISE_INTERNAL_ERROR`；固定种子全迭代复现，纯内存逻辑
与平台无关。

## 修法
1. 消费方是外部 QUIC 栈 → **保持默认 boring-quic-api，不传 enable-quic**
   （生态同形：libmsquic 2.5.7 vendored configure = 裸 `Configure linux-aarch64`）
2. provider 功能面由 test_package 实质验证（boring-quic API 逐项调用断言）
3. 需要 OSSL_QUIC 原生栈 → 迁移后继仓库 quictls/quictls，勿用 3.3.0-quic1 tag
4. 若确需 enable-quic → 必须同时显式 no-boring-quic-api（否则 Configure die）

## 验证
- quictls/3.3.0-quic1 conan-verify 8 门禁全绿（2026-09-29）
- make test（boring-quic-api 交付配置）Files=312 Tests=3185 Result: PASS
- 对照 enable-quic 配置：QUIC 14 套 12 通过 / 2 确定性上游失败
