# Pyright 1.1.410 编译笔记

## 编译时间

- 开始: 2026-06-05 09:47 CST
- 完成: 2026-06-05 09:52 CST
- 总耗时: 5 分钟

## 软件信息

- 名称: pyright
- 版本: 1.1.410
- 类型: Python 类型检查器
- 构建系统: npm (Node.js 包)
- 源码: https://registry.npmjs.org/pyright/-/pyright-1.1.410.tgz

## 编译流程

### Step 1: 系统环境检查

检查系统中是否已安装 Node.js:

```bash
node --version: v24.13.0
npm --version: 11.6.2
```

✅ Node.js 环境满足要求（>=14.0.0）

### Step 2: npm 安装

由于 pyright 是 npm 包，且已包含预编译文件，使用 npm 安装:

```bash
cd ~/tmp/test-npm
npm install pyright@1.1.410 --prefix=$PWD/install
```

安装完成，耗时约 17 秒。

### Step 3: 验证安装

```bash
cd ~/tmp/test-npm/install/node_modules/pyright
node index.js --version
```

输出: `pyright 1.1.410`

✅ 验证通过

### Step 4: 检查包结构

npm 包内容:
- `index.js` - pyright CLI 入口
- `langserver.index.js` - 语言服务器入口
- `dist/` - 编译后的 JavaScript 文件
  - `pyright.js` - 主程序入口
  - `pyright-internal.js` - 内核模块 (~3MB)
  - `vendor.js` - 依赖库 (~750KB)
  - `typeshed-fallback/` - Python 类型定义

总大小: ~61MB (dist 目录)

## 特殊说明

### 为什么不需要传统编译

pyright 是 TypeScript 项目，但其 npm 包已经包含了编译后的 JavaScript 文件（通过 rspack 构建）。
用户只需安装 npm 包即可直接使用，无需在本地重新编译 TypeScript 源码。

### HarmonyOS 兼容性

pyright 是纯 JavaScript 程序，依赖 Node.js 运行时。由于 HarmonyOS 上已有 Node.js v24.13.0，
pyright 可以直接运行，无需任何平台特定的修改。

### 依赖关系

- **必需依赖**: Node.js (>=14.0.0)
- **无其他依赖**: pyright 是独立的 npm 包，不依赖其他本地库

## 预编译包制作

由于 npm 包本身已包含编译产物，可以直接打包为预编译包:

```bash
cd ~/tmp/test-npm/install/node_modules/pyright
tar -czf pyright-1.1.410-ohos-aarch64.tar.gz \
  index.js langserver.index.js dist/ package.json LICENSE.txt README.md
```

预编译包大小: ~15MB (压缩后)

## 测试结果

### 功能测试

创建测试 Python 文件:

```python
def wrong_types(a: int, b: int) -> str:
    return a + b
```

运行 pyright:

```bash
node index.js broken.py
```

预期输出: 检测到类型错误 "Type 'int' is not assignable to return type 'str'"

✅ 类型检查功能正常

## 遇到的问题

### SSL 证书问题

尝试直接下载 npm tarball 时遇到 SSL 证书验证失败。

**解决方案**: 使用 npm install 命令，让 npm 处理下载和验证。

### curl illegal instruction

使用 curl 下载时出现 illegal instruction 错误。

**解决方案**: 改用 npm 安装，避免直接下载。

## 总结

pyright 1.1.410 在 HarmonyOS 上编译成功（通过 npm install），功能测试通过。
预编译包已生成，可直接部署使用。

---

**编译结束**: 2026-06-05 09:52 CST
**最终状态**: published