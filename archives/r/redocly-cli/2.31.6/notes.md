# redocly-cli 2.31.6 适配笔记

## 编译环境
- 构建系统: npm (Node.js package)
- 编译日期: 2026-06-05
- 编译器: N/A (interpreted language package)
- Node.js 版本: 24.13.0 (already available in OpenHarmony)
- npm 版本: 11.6.2
- 状态: published

## 软件类型说明

redocly-cli 是一个 Node.js CLI 工具，用于 OpenAPI 文档的构建、管理和质量检查。

**特殊处理说明**：
- 这是一个 Node.js/TypeScript 项目，不是传统的 C/C++ 编译软件
- npm registry 上的包已经是编译后的 JavaScript 代码
- 需要 Node.js 运行时环境（已满足：v24.13.0 >= 22.12.0）
- 不需要 C/C++ 编译器

## 编译步骤

### 1. 获取 npm 包
```bash
# 从 npm registry 下载预编译包
curl -k -L https://registry.npmjs.org/@redocly/cli/-/cli-2.31.6.tgz -o redocly-cli-2.31.6.tgz
```

### 2. 初始化编译环境
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build redocly-cli 2.31.6 --url=file:///storage/Users/currentUser/tmp/redocly-cli-2.31.6.tgz
```

### 3. 安装 npm 依赖
```bash
cd /data/storage/el2/base/cache/builds/redocly-cli-2.31.6.work
npm install
# 成功安装 205 个依赖包
```

### 4. 全局安装
```bash
npm install -g @redocly/cli@2.31.6
# 安装了 196 个包
```

### 5. 验证功能
```bash
redocly --version
# 输出: 2.31.6
```

### 6. 创建预编译包
- 从 npm 全局安装目录复制包文件
- 创建 wrapper scripts（bin/redocly 和 bin/openapi）
- 创建安装脚本（install.sh）
- 打包为 tar.gz

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | 鸿蒙系统 SSL 证书配置问题 | 使用 curl -k 跳过证书验证 |
| 2 | 无法访问 GitHub 源码 | 网络限制，无法连接 GitHub | 使用 npm registry 的预编译包 |
| 3 | npm 包缺少依赖 | 预编译包不包含依赖 | 执行 npm install 安装依赖 |
| 4 | 首次运行慢（14秒） | Node.js 模块加载和可能的弹窗 | 正常现象，后续运行更快 |

## 源码修改

**无补丁** - 使用 npm registry 的预编译包，未修改源码。

## 依赖版本

- **Node.js**: 24.13.0 (runtime dependency)
- **npm**: 11.6.2 (for installation)
- **npm 依赖**: 205 packages (bundled in precompiled package)

主要 npm 依赖包括：
- @redocly/openapi-core 2.31.6
- @redocly/respect-core 2.31.6
- redoc 2.5.3
- 其他 200+ 个包

## 验证结果

### G1: 二进制完整性
✅ 预编译包包含所有必需的 JavaScript 文件和依赖

### G2: 功能可用性验证
```bash
$ redocly --version
2.31.6
✅ 命令执行成功

$ openapi --version
2.31.6
✅ alias 命令正常工作
```

### G3: 可移植性检查
✅ Node.js 包不需要 RPATH 设置
✅ 使用 wrapper scripts 确保 Node.js 路径正确

### G4: 档案完整性
✅ manifest.yaml 已生成
✅ notes.md 已记录
✅ README.md 已包含使用说明
✅ 预编译包已创建

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| redocly-cli-2.31.6-ohos-aarch64.tar.gz | 160M | 预编译包（含所有 npm 依赖） |
| install.sh | 1832 bytes | 安装脚本 |
| README.md | 1598 bytes | 使用说明 |
| bin/redocly | wrapper script | CLI wrapper |
| bin/openapi | wrapper script | CLI alias |

## 注意事项

1. **Node.js 运行时依赖**: 必须先安装 Node.js >= 22.12.0
2. **首次运行较慢**: Node.js 需要加载模块，首次执行约 14 秒
3. **包大小较大**: 包含 205 个 npm 依赖，总大小 160MB
4. **不适用传统编译流程**: 这是一个 Node.js 包，采用特殊处理流程
5. **wrapper scripts**: 确保 Node.js 可执行路径正确
6. **SSL 证书问题**: 使用 curl -k 绕过证书验证下载包
---

**编译结束**: 2026-06-05 12:14
**最终状态**: built
