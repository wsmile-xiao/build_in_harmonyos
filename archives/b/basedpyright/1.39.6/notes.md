# basedpyright 1.39.6 适配笔记

## 编译环境
- 构建系统: npm (Node.js package)
- 编译日期: 2026-06-05
- 编译器: N/A (npm 包，无需编译)
- 状态: published

## 编译步骤

basedpyright 是一个基于 pyright 的 Python 类型检查器，以 Node.js 包形式分发。

### 安装方式对比

**pip 安装尝试（失败）**：
```bash
python3 -m pip install basedpyright
```
失败原因：依赖 nodejs-wheel-binaries 需要从源码编译 nodejs，编译过程中遇到 C++ 错误：
- ada 库 lambda 表达式变量捕获问题
- 编译耗时超过 4 分钟后失败

**npm 安装（成功）**：
```bash
npm install -g basedpyright@1.39.6
```
成功原因：使用系统已预装的 nodejs v24.13.0，无需编译 nodejs。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pip 安装 SSL 证书验证失败 | 网络环境 SSL 配置问题 | 使用清华 PyPI 镜像 |
| 2 | nodejs-wheel-binaries 编译失败 | C++ lambda 捕获语法错误，ada 库编译问题 | 改用 npm 安装，使用系统 nodejs |
| 3 | 传统编译流程不适用 | basedpyright 是 Node.js 包，非 C/C++ 软件 | 使用 npm install -g |

## 源码修改

无补丁。npm 包直接安装，无需修改源码。

## 依赖版本

| 软件 | 版本 | 来源 |
|------|------|------|
| nodejs | v24.13.0 | 系统预装 |
| npm | 11.6.2 | 系统预装 |
| Python | 3.12.8 | 系统预装 |

## 验证结果

```bash
$ basedpyright --version
basedpyright 1.39.6
based on pyright 1.39.6

$ which basedpyright
/storage/Users/currentUser/.opendesk/interpreters/npm-global/bin/basedpyright

$ npm list -g basedpyright
/storage/Users/currentUser/.opendesk/interpreters/npm-global/lib
└── basedpyright@1.39.6
```

## 交付物

| 文件 | 说明 |
|------|------|
| npm-global/bin/basedpyright | 基于 pyright 的 Python 类型检查器 |
| npm-global/lib/node_modules/basedpyright/ | npm 包安装目录 |

**安装路径**: `/storage/Users/currentUser/.opendesk/interpreters/npm-global/bin/basedpyright`

## 注意事项

1. **特殊软件类型**: basedpyright 是 Node.js 包，不适合使用传统 ohc-run.py build 流程
2. **依赖优先**: 使用系统已预装的 nodejs，避免 nodejs-wheel-binaries 编译失败
3. **替代方案**: pip 安装失败时，npm 安装是可行的替代方案
4. **版本匹配**: basedpyright 1.39.6 基于 pyright 1.39.6

---

**编译开始**: 2026-06-05 10:31

**编译结束**: 2026-06-05 10:44

**最终状态**: published (npm 安装成功)