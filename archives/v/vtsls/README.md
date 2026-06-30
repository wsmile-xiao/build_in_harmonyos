# @vtsls/language-server

## 简介

LSP wrapper for TypeScript extension of VSCode. 提供完整的 TypeScript 语言服务器功能，与 VSCode 的 TypeScript 扩展功能基本一致。

## 功能概述

- TypeScript/JavaScript 语言服务器（LSP）
- 代码补全、导航、重构
- 类型检查和错误诊断
- 快速修复和代码操作
- 与 VSCode TypeScript 扩展功能一致

## OHOS 适配要点

### 构建环境

- **Node.js**: 需要 Node.js >= 16
- **pnpm**: 包管理器（pnpm >= 10）
- **Git submodule**: 需要初始化 vscode submodule

### HMDFS 限制

- **E079**: HMDFS 不支持硬链接
- **解决方案**: 设置 `pnpm config set store-dir /data/storage/el2/base/cache/pnpm-store`
- **原因**: pnpm 的 content-addressable store 使用硬链接

### 构建流程

```bash
git clone --no-hardlinks https://github.com/yioneko/vtsls.git
cd vtsls
git submodule update --init --depth=1
pnpm install
pnpm build
```

### 安装方式

```bash
# 方式1：通过 npm 安装
npm install -g @vtsls/language-server

# 方式2：使用预编译包
tar -xzf vtsls-language-server-0.3.0.tgz
cd package
npm install --production
```

## 依赖关系

### 构建依赖

- Node.js >= 16
- pnpm >= 10
- Git

### 运行依赖

- Node.js >= 16
- TypeScript（可选，可使用 bundled 版本）

## 注意事项

- 预编译包不包含依赖，需要通过 npm install 安装
- 运行时需要 Node.js 环境
- 不是 ELF 二进制，无需签名

## 参考资料

- GitHub: https://github.com/yioneko/vtsls
- npm: https://www.npmjs.com/package/@vtsls/language-server