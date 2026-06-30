# redocly-cli

## 软件简介

Redocly CLI is your all-in-one OpenAPI utility. It builds, manages, improves, and quality-checks your API descriptions.

## 功能概述

- **Lint**: Validate OpenAPI specifications with customizable rules
- **Bundle**: Combine multiple OpenAPI files into a single file
- **Build-docs**: Generate beautiful API documentation
- **Split**: Split a large OpenAPI file into multiple files
- **Join**: Join multiple OpenAPI files with shared components
- **Push**: Push API descriptions to Redocly API registry

## OHOS 适配说明

### 特殊处理

redocly-cli 是一个 Node.js/TypeScript 项目，不是传统的 C/C++ 编译软件。针对 OpenHarmony 的适配要点：

1. **运行时依赖**: 需要 Node.js >= 22.12.0 或 >= 20.19.0 < 21.0.0
   - OpenHarmony 已安装 Node.js v24.13.0，满足要求

2. **包类型**: npm registry 的预编译 JavaScript 包
   - 不需要源码编译
   - 使用 `npm install` 安装依赖

3. **包装脚本**: 使用 wrapper scripts 确保 Node.js 路径正确
   - `/data/service/hnp/bin/node` 是 OpenHarmony 的 Node.js 路径

4. **首次运行**: Node.js 需要加载模块，首次执行较慢（约 14 秒）

### 与 Linux 的差异

- Linux: 通常通过 `npm install -g @redocly/cli` 全局安装
- OpenHarmony: 使用预编译包 + wrapper scripts 的方式

## 依赖关系

### 编译依赖
- Node.js >= 22.12.0
- npm >= 10

### 运行依赖
- Node.js runtime

## 参考资料

- **官网**: https://redocly.com
- **CLI 文档**: https://redocly.com/docs/cli
- **源码仓库**: https://github.com/Redocly/redocly-cli
- **npm 包**: https://www.npmjs.com/package/@redocly/cli
- **Homebrew Formula**: https://formulae.brew.sh/formula/redocly-cli

## 版本历史

- **2.31.6** (2026-06-05): Published to cmd-pkgs
  - 首次适配 OpenHarmony
  - 使用 npm registry 预编译包
  - 包含完整的 npm 依赖（205 packages）