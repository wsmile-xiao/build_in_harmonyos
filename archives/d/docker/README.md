# docker

Docker CLI 是 Docker 容器平台的命令行工具，用于管理容器、镜像、网络和卷。

## 描述
Docker CLI 是用于与 Docker 引擎交互的命令行客户端。支持容器生命周期管理、镜像构建与拉取、网络和存储卷配置等操作。

## 已编译版本
- 29.5.3 (2026-06-17)

## 依赖
- Go 1.26.0

## 特性
- 容器创建、启动、停止、删除
- 镜像构建（docker build）、拉取、推送
- 网络和卷管理
- Compose 集成
- 多平台构建支持

## 补丁
- 0001-go.mod.patch: 降级 Go 版本声明以适配本地 Go 工具链
- 0002-go.sum.patch: 对应 go.mod 降级的 checksum 更新

## 使用方法
```bash
# 运行容器
docker run -it ubuntu bash

# 构建镜像
docker build -t myapp .

# 查看运行中的容器
docker ps
```

## 注意事项
- CGO_ENABLED=0 编译，纯静态二进制
- 需要 containerd 运行时配合使用
