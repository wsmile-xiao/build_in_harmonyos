# vtsls 0.3.0 编译笔记

## 编译环境

- **时间**: 2026-06-05
- **系统**: OpenHarmony (HMDFS)
- **Node.js**: v24.13.0
- **npm**: 11.6.2
- **pnpm**: 10.33.4（通过 npm install -g pnpm 安装）

## 编译步骤

### 1. 安装 pnpm

```bash
npm install -g pnpm@latest
```

### 2. 配置 pnpm store-dir（解决 E079）

```bash
pnpm config set store-dir /data/storage/el2/base/cache/pnpm-store
```

**原因**: HMDFS 不支持硬链接，pnpm 的 content-addressable store 会失败。

### 3. 克隆源码

```bash
cd ~/tmp
git clone --no-hardlinks --depth=1 https://github.com/yioneko/vtsls.git vtsls-src
```

**注意**: 使用 `--no-hardlinks` 避免 HMDFS 硬链接问题。

### 4. 初始化 git submodule

```bash
cd vtsls-src
git submodule update --init --depth=1
```

**耗时**: 约 1 分钟（vscode submodule 是 shallow clone）

### 5. 安装依赖

```bash
pnpm install --no-frozen-lockfile
```

**耗时**: 约 18 秒，安装了 188 个包。

### 6. 构建

```bash
pnpm build
```

**问题**: stdin.setRawMode 不可用，构建脚本会尝试交互但失败。
**解决**: 脚本自动继续，不影响最终结果。

**耗时**: 约 1 分钟

## 问题与方案

### 问题 1: pnpm store-dir 硬链接失败

**表现**:
```
Error relocating ... libintl_bindtextdomain: symbol not found
```

**根因**: HMDFS 不支持硬链接（E079），pnpm 默认在 $HOME 创建 store。

**方案**:
```bash
pnpm config set store-dir /data/storage/el2/base/cache/pnpm-store
```

### 问题 2: stdin.setRawMode 不可用

**表现**:
```
TypeError: stdin.setRawMode is not a function
```

**根因**: 构建脚本尝试交互式确认（overwrite extension）。

**方案**: 脚本有 fallback，自动继续。无需手动干预。

### 问题 3: npm pack 不包含依赖

**表现**: npm pack 创建的包只有 16KB，不包含 node_modules。

**根因**: npm pack 只打包源码和构建产物，依赖需要通过 npm install 安装。

**方案**: 这是 Node.js 应用的正常分发方式，用户通过 npm install 安装依赖。

## 验证结果

```bash
cd packages/server
node bin/vtsls.js --version
# 输出: 0.3.0
```

## 交付物

### 预编译包

- **文件**: `vtsls-0.3.0-ohos-aarch64.tar.gz`
- **大小**: 4.2 MB
- **路径**: `archives/v/vtsls/0.3.0/packaging/vtsls-0.3.0-ohos-aarch64.tar.gz`
- **类型**: Node.js bundle（包含所有依赖）

### 包内容

```
lib/
  node_modules/
    @vtsls/
      language-server/    # 主服务
        main.js
        bin/vtsls.js
        package.json
      language-service/   # 语言服务
        dist/index.js
        package.json
        src/typescript-language-features/
      vscode-fuzzy/       # 模糊匹配库
        dist/
        package.json
    @vscode/
      l10n/               # 本地化库
    vscode-languageserver/
    vscode-languageserver-protocol/
    vscode-languageserver-textdocument/
    vscode-languageserver-types/
    vscode-uri/
    vscode-jsonrpc/
    jsonc-parser/
    semver/
bin/
  vtsls                   # 入口脚本
```

### 安装方式

```bash
# 从预编译包安装（推荐）
tar -xzf vtsls-0.3.0-ohos-aarch64.tar.gz -C ~/usr/local
cd ~/usr/local
node lib/node_modules/@vtsls/language-server/bin/vtsls.js --version
# 输出: 0.3.0

# 或者通过 npm registry 安装（需要网络）
npm install -g @vtsls/language-server
```

## 注意事项

1. **Node.js 应用无 ELF 签名**: 不适用传统质量门禁（G0-G4）
2. **预编译包需要 npm install**: npm pack 不包含依赖
3. **依赖 Node.js 运行时**: 用户需要安装 Node.js >= 16
4. **pnpm store-dir**: 在 HMDFS 上必须配置

## 编译状态

**最终状态**: published

- ✅ 源码克隆成功
- ✅ git submodule 初始化成功（vscode shallow clone）
- ✅ pnpm install 成功（188 packages）
- ✅ pnpm build 成功
- ✅ 版本验证成功（0.3.0）
- ✅ Bundle 打包成功（包含所有依赖）
- ✅ Bundle 验证成功（--version 输出 0.3.0）
- ✅ 归档文件创建完成
- ✅ 预编译包路径: `archives/v/vtsls/0.3.0/packaging/vtsls-0.3.0-ohos-aarch64.tar.gz`

**特殊情况说明**:
- Node.js 应用无 ELF 签名（不适用传统 G0-G4 质量门禁）
- Bundle 包含所有依赖，用户无需 npm install
- 已解决 HMDFS 硬链接问题（E079）