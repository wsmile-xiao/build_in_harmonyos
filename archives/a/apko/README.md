# apko

apko 是 Chainguard 开发的基于 APK 包直接构建 OCI 容器镜像的工具。

## 描述
apko 可以从 APK（Alpine Package Keeper）包直接构建最小化的 OCI 容器镜像，无需 Dockerfile 或 Docker daemon。它专注于安全、最小化和可重现的容器镜像构建。

## 已编译版本
- 1.2.17 (2026-06-17)

## 依赖
- Go 1.26.0

## 特性
- 直接从 APK 包构建 OCI 镜像
- 无需 Docker daemon
- 可重现构建
- SBOM（软件物料清单）生成
- 多架构支持
- 最小化镜像

## 使用方法
```bash
# 构建镜像
apko build config.yaml myimage:latest output.tar

# 发布到 registry
apko publish config.yaml myregistry/myimage:v1
```

## 注意事项
- CGO_ENABLED=0 编译，纯静态二进制，无需源码修改
