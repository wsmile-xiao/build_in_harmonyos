# boost-build

## 简介
Boost.Build（b2/bjam）是 Boost C++ 库使用的构建系统，也可用于非 Boost 项目。
它提供基于 Jam 的声明式构建描述语言，支持多工具集、多平台、多变体构建。

## 版本
1.90.0（对应 boost-1.90.0 标签）

## 构建系统
自定义构建系统 — 使用 bootstrap.sh 构建 b2 引擎，然后用 `b2 install` 安装部署。
**不使用**标准的 autotools/cmake/meson 构建流程。

## 许可证
BSL-1.0（Boost 软件许可证）

## 主要产物
- b2: Boost.Build 引擎可执行文件

## 构建说明
1. 使用 `bootstrap.sh --cxx=clang++` 构建 b2 引擎
2. 使用 `b2 install --prefix=$DEFAULT_PREFIX toolset=clang` 安装
3. b2 不支持 DESTDIR 模式；需手动创建 staging 目录
4. 必须指定 `toolset=clang`，否则默认使用不存在的 gcc

## 验证结果
```
$ b2 --version
B2 5.3.2 (OS=LINUX, jobs=20)
```

## 平台限制
- b2 不支持 DESTDIR，需手动处理 staging 目录
- 部分 b2 自测默认使用 gcc 工具集，在 OpenHarmony 上预期失败
- `b2 --help` 有 HMDFS scandir 权限警告，不影响核心功能