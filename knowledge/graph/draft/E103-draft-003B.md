# E103: OpenSSL 3.5 API 兼容性问题

## 问题现象

编译时出现以下错误：

```
error: use of undeclared identifier 'SSL_OP_NO_RENEGOTIATION'
error: call to undeclared function 'SSL_get1_peer_certificate'
error: use of undeclared identifier 'SSL_trace'
```

## 根因分析

OpenSSL 3.5.6 移除/重命名了部分 API：

1. **SSL_OP_NO_RENEGOTIATION** → 改为 `SSL_OP_NO_CLIENT_RENEGOTIATION`
2. **SSL_get1_peer_certificate** → 不存在，应使用 `SSL_get_peer_certificate`
3. **SSL_trace** → 函数被移除，新版本使用 `OSSL_trace_*` API

这些 API 变化主要影响：
- ustream-ssl（OpenWrt SSL 库）
- 其他直接使用 OpenSSL 内部 API 的软件

## 解决方案

### 方案 1：源码补丁（推荐）

应用 OpenSSL 3.5 兼容性补丁：

```bash
# 修复 SSL_OP_NO_RENEGOTIATION
sed -i 's/SSL_OP_NO_RENEGOTIATION/SSL_OP_NO_CLIENT_RENEGOTIATION/g' ustream-openssl.c

# 修复 SSL_get1_peer_certificate
sed -i 's/SSL_get1_peer_certificate/SSL_get_peer_certificate/g' ustream-openssl.c

# 修复 SSL_trace（禁用 trace 功能）
sed -i 's/SSL_CTX_set_msg_callback(ctx->ssl, SSL_trace)/SSL_CTX_set_msg_callback(ctx->ssl, NULL)/g' ustream-openssl.c
```

### 方案 2：版本降级

如果补丁不可行，可以降级到 OpenSSL 3.2+：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- openssl 3.2.0
```

## 验证

修复后验证：

```bash
grep -E "SSL_OP_NO_RENEGOTIATION|SSL_trace|SSL_get1_peer_certificate" *.c
# 应返回空（或已替换为新 API）

cmake --build build
# 编译应成功通过
```

## 受影响软件

- ustream-ssl（20260222-r0 及相关版本）
- 其他 OpenWrt 相关 SSL 库

## 注意事项

1. **API 变化是正常的**：OpenSSL 在不同版本间会调整 API，这是正常的演进。
2. **检查 OpenSSL 版本**：编译前确认 OpenSSL 版本：`pkg-config --modversion openssl`
3. **阅读 OpenSSL 文档**：迁移指南：https://www.openssl.org/docs/man3.5/man7/migration_guide.html

## 相关案例

- ustream-ssl 20260222-r0（2026-05-22）：应用补丁后编译成功

---

*Draft created by 003B on 2026-05-22*