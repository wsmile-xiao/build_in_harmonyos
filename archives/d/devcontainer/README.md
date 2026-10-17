# devcontainer

Dev Containers CLI 是用于创建和管理开发容器的命令行工具。

## 描述
devcontainer CLI 允许开发者使用容器作为完整的开发环境。支持 VS Code Dev Containers 规范，可以创建、配置和管理开发容器，确保团队开发环境一致性。

## 已编译版本
- 0.87.0 (2026-08-06, conan 适配)

## 依赖
- Node.js 24.13.0

## 特性
- 开发容器创建与配置
- devcontainer.json 规范支持
- Docker Compose 和 Kubernetes 集成
- 特性（Features）和模板（Templates）支持
- 生命周期钩子

## 使用方法
```bash
# 创建开发容器
devcontainer up

# 在容器中执行命令
devcontainer exec <command>

# 构建开发容器镜像
devcontainer build
```

## 注意事项
- npm 项目，仅编译原生模块 node-pty
- 无需源码修改，无补丁文件
- Conan 配方: conanfile.py (package_type=application, build system=npm)
