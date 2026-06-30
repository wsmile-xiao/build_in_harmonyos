# eslint_d

> Speed up eslint to accelerate your development workflow

**版本**: 15.0.2
**编译日期**: 2026-06-05
**构建系统**: npm
**依赖**: Node.js >= 22

## 简介

eslint_d 是 ESLint 的守护进程版本，可以让 ESLint 运行得更快。它通过保持 ESLint 进程常驻内存，避免每次 lint 时重新启动 Node.js 进程和加载 ESLint 配置。

## 安装

### 从预编译包安装（推荐）

```bash
# 下载预编译包
tar -xzf eslint_d-15.0.2-ohos-aarch64.tar.gz -C ~/usr/local

# 验证安装
node ~/usr/local/lib/node_modules/eslint_d/bin/eslint_d.js --version
# 输出: eslint_d: v15.0.2, bundled eslint: v10.0.3
```

### 从 npm registry 安装

```bash
npm install -g eslint_d
```

## 使用

```bash
# 启动守护进程
eslint_d start

# 运行 lint
eslint_d [file.js] [dir]

# 停止守护进程
eslint_d stop

# 查看状态
eslint_d status
```

## 编译说明

### 编译环境

- Node.js: v24.13.0
- npm: 11.6.2

### 编译步骤

1. 克隆源码：`git clone https://github.com/mantoni/eslint_d.js.git`
2. 安装依赖：`npm install`
3. 运行测试：`npm test` (114 passing)
4. 创建预编译包：包含所有依赖的 bundle

### 特殊说明

- Node.js 应用，不适用传统 ELF 签名
- 预编译包包含所有依赖（93 MB）
- 需要 Node.js >= 22 运行时

## 文件

- `archives/e/eslint_d/15.0.2/packaging/eslint_d-15.0.2-ohos-aarch64.tar.gz` - 预编译包
- `archives/e/eslint_d/15.0.2/notes.md` - 编译笔记
- `archives/e/eslint_d/15.0.2/manifest.yaml` - 版本元数据

## 依赖

- Node.js >= 22

## 预编译包内容

```
lib/node_modules/eslint_d/
  package.json
  bin/eslint_d.js
  bin/eslint.js
  lib/
    commands.js
    config.js
    daemon.js
    ...
  node_modules/
    debug/
    eslint/
    supports-color/
    ... (268 packages)
bin/
  eslint_d  # 入口脚本
```

## 许可证

MIT License

## 参考资料

- GitHub: https://github.com/mantoni/eslint_d.js
- npm: https://www.npmjs.com/package/eslint_d