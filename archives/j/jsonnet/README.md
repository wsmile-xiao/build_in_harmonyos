# jsonnet

Jsonnet 是一种数据模板语言，用于配置文件的生成和管理。它是 JSON 的扩展，增加了变量、函数、条件、导入等特性。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| v0.20.0 | built | 最新稳定版本，支持 Makefile 构建 |

## 软件信息

- **官网**: https://jsonnet.org/
- **源码**: https://github.com/google/jsonnet
- **描述**: Jsonnet 是一种模板语言，用于生成 JSON/YAML 配置文件

## 构建系统

jsonnet 同时提供两种构建方式：
- **Makefile**: 推荐在 OpenHarmony 上使用
- **CMake**: CMakeLists.txt 版本要求过旧（cmake_minimum_required 2.8.7）

## 平台适配要点

1. HMDFS 文件系统不支持 `ln -sf` 覆盖，需使用 `rm -f && ln -s` 替代
2. 无外部依赖（内置 rapidyaml 和 md5 库）
3. 测试套件较大（770+ 测试），建议使用 timeout 控制
4. 使用 Makefile 构建时无需 configure 步骤（纯 Makefile 项目）