# cosign

Cosign 是 Sigstore 项目提供的容器镜像签名和验证工具。

## 描述
Cosign 支持对 OCI 容器镜像进行签名、验证和存储。它与 Sigstore 生态系统（Fulcio 证书颁发、Rekor 透明日志）集成，提供无密钥签名体验。

## 已编译版本
- 3.1.1 (2026-06-17)

## 依赖
- Go 1.26.0

## 特性
- 容器镜像签名与验证
- Keyless 签名（OIDC 身份验证）
- 透明日志集成
- 多种签名存储方式（OCI registry、本地文件等）
- 批量签名验证

## 使用方法
```bash
# 签名镜像
cosign sign myregistry/myimage:v1

# 验证镜像签名
cosign verify myregistry/myimage:v1

# Keyless 签名
cosign sign --keyless myregistry/myimage:v1
```

## 注意事项
- CGO_ENABLED=0 编译，纯静态二进制，无需源码修改
