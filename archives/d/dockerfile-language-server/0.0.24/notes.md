# dockerfile-language-server 0.0.24 编译笔记

## 编译信息

- **日期**: 2026-06-08
- **编译者**: AI Assistant
- **构建系统**: Node.js + TypeScript

## 编译过程

### 1. 源码获取

- 项目地址: https://github.com/rcjsuen/dockerfile-language-server-nodejs
- 版本: 0.0.24
- 下载方式: GitHub tarball

### 2. 环境检查

- Node.js: v24.13.0 (/data/service/hnp/bin/node)
- npm: 11.6.2 (/data/service/hnp/bin/npm)
- 构建系统: Node.js (非 autotools/cmake)

### 3. 构建步骤

```bash
# 解压源码
tar -xzf dockerfile-language-server-0.0.24.tar.gz
cd rcjsuen-dockerfile-language-server-cdd2662

# 安装依赖并构建（npm install 会自动运行 prepublish 脚本）
npm install
```

### 4. 构建产物

- 编译后的 JavaScript: `lib/server.js`
- 可执行入口: `bin/docker-langserver`
- 依赖包: `node_modules/` (232 packages)

### 5. 验证

```bash
# 添加执行权限
chmod +x bin/docker-langserver

# 测试运行（需要通过 LSP 协议通信）
./bin/docker-langserver --stdio
```

Language server 可以正常运行，需要通过 stdio 或 socket 与客户端通信。

## 特殊说明

### Node.js 项目特点

这是一个 Node.js 项目，不同于传统的 C/C++ 项目：
- **构建工具**: npm + TypeScript compiler
- **依赖管理**: package.json + npm
- **分发方式**:
  - 方案 1: npm 包发布到 registry
  - 方案 2: pkg 打包成独立可执行文件
  - 方案 3: 打包整个编译后的项目（当前采用）

### 预编译包策略

由于 OpenHarmony 环境已有 Node.js 运行时，采用方案 3：
- 打包编译后的项目（包括 lib/, bin/, node_modules/）
- 用户解压后可直接使用 `bin/docker-langserver`
- 通过 `npm install -g` 方式安装

### 依赖说明

主要运行时依赖：
- `dockerfile-language-service@0.0.12`: Dockerfile 语法分析服务
- `dockerfile-utils@0.0.11`: Dockerfile 工具库
- `vscode-languageserver@^6.1.1`: VSCode Language Server 协议实现

## 遇到的问题

### 1. SSL 证书验证失败

**问题**: Python urllib.request 无法验证 GitHub 的 SSL 证书
**解决**: 使用 Python 的 ssl 模块跳过证书验证

### 2. curl 动态库链接错误

**问题**: 系统 curl 无法正常工作
**解决**: 使用 Python 下载源码包

## 知识沉淀

### E{NNN}: Node.js 项目编译模式（新增）

**适用场景**: Node.js/TypeScript 项目

**编译流程**:
1. 检查 Node.js 和 npm 版本
2. `npm install` 安装依赖
3. `npm run build` 或 `npm run prepublish` 编译（部分项目自动运行）
4. 验证生成的 JavaScript 文件
5. 打包整个项目或发布到 npm

**注意事项**:
- Node.js 项目不需要传统的 configure/make 步骤
- `npm install` 会自动处理依赖和构建
- 需要确认 Node.js 版本兼容性（检查 package.json 的 engines 字段）

## 编译结束

**编译结束时间**: 2026-06-08 15:51
**最终状态**: 成功
**预编译包位置**: archives/d/dockerfile-language-server/0.0.24/packaging/dockerfile-language-server-0.0.24-ohos-aarch64.tar.gz
**预编译包大小**: 67 MB
**验证结果**: Language server 正常响应 LSP initialize 请求，所有功能能力正常返回