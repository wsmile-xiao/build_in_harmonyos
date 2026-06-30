# carburetor

> GTK/libadwaita frontend for the Tractor anonymity project

## 简介

carburetor 是 Tractor 项目的图形前端，基于 GTK4/libadwaita，用于配置和管理 Tor 匿名网络连接。原项目使用 Python/pyproject.toml 构建，为适配 OHOS 预编译框架创建了 meson.build 构建文件。

## OHOS 适配要点

- 纯 Python GTK 项目，原始构建系统为 flit（pyproject.toml），非 meson/cmake
- 为适配 OHOS 预编译框架，创建了 meson.build 和 bin/carburetor 入口脚本
- 运行时需要 GTK4/libadwaita/gi 等图形库和 tractor Python 包

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python 3 | 3.12 | 运行时依赖 |
| GTK4 | 4.0 | GUI 库（运行时） |
| libadwaita | 1 | UI 组件库（运行时） |
| tractor | - | Tor 匿名服务管理（运行时） |

## 功能验证

```bash
# 检查安装的 Python 模块
ls ~/usr/local/share/carburetor/
```

## 参考

- [源码仓库](https://framagit.org/tractor/carburetor)