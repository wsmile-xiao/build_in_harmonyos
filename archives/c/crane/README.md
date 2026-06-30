# crane

Crane 是一个用于与远程容器镜像和仓库交互的工具，由 Google 开发（go-containerregistry 项目）。

## 描述

Crane 可以拉取、推送、列出、复制和修改容器镜像，无需运行 Docker daemon。它是 skopeo 的替代方案，适用于 CI/CD 和镜像管理场景。

## 已编译版本
- 0.21.6 (2026-05-26) — 预编译二进制

## 依赖
- 无额外依赖（预编译二进制方案）

## 特性
- 拉取/推送容器镜像
- 列出镜像标签和层
- 复制镜像到不同仓库
- 修改镜像配置
- 不依赖 Docker daemon

## 使用方法
```bash
# 查看版本
crane version

# 列出镜像标签
crane ls <repository>

# 拉取镜像
crane pull <image> <output>
```

## 注意事项
- Go 语言项目在 HMDFS 上无法源码编译，使用官方预编译二进制 + ohc sign-elf 签名部署
- 使用 `crane version` 查看版本，不支持 `--version` flag