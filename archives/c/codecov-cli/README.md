# codecov-cli

codecov-cli 是 Codecov 代码覆盖率报告服务的命令行上传工具。

## 描述

codecov-cli 是一个 Node.js/TypeScript CLI 工具，用于将代码覆盖率数据上传到 Codecov 平台。它支持多种覆盖率报告格式（Cobertura, JaCoCo, lcov 等），并提供覆盖率分析和报告功能。

## 已编译版本

- 0.8.0 (2026-05-27)

## 依赖

- Node.js (运行时依赖)

## OHOS 适配说明

- Node.js/TypeScript 项目，通过 npm build 编译 TypeScript
- 使用 shell wrapper 脚本（bin/codecov）调用 Node.js 运行

## 使用方法

```bash
# 上传覆盖率报告
codecov upload-process -f coverage.xml
```