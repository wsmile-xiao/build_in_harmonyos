# eslint_d 15.0.2 编译笔记

## 编译环境

- **时间**: 2026-06-05
- **系统**: OpenHarmony (HMDFS)
- **Node.js**: v24.13.0
- **npm**: 11.6.2

## 编译步骤

### 1. 克隆源码

```bash
cd ~/tmp/builds
git clone --no-hardlinks --depth=1 https://gh-proxy.com/https://github.com/mantoni/eslint_d.js.git package
```

**注意**: 使用 GitHub 加速代理 `gh-proxy.com` 避免网络问题。

### 2. 安装依赖

```bash
cd package
npm install
```

**耗时**: 约 34 秒

**说明**: prepare 脚本会自动运行 husky 和安装 fixture 依赖。

### 3. 运行测试

```bash
npm test
```

**结果**: 114 passing (440ms)

### 4. 创建预编译包

```bash
# 创建安装目录结构
mkdir -p staging/lib/node_modules/eslint_d staging/bin

# 复制文件
cp -r package.json lib bin node_modules staging/lib/node_modules/eslint_d/

# 创建启动脚本
cat > staging/bin/eslint_d << 'EOF'
#!/bin/sh
NODE_PATH="/storage/Users/currentUser/usr/local/lib/node_modules/eslint_d/node_modules"
exec node "/storage/Users/currentUser/usr/local/lib/node_modules/eslint_d/bin/eslint_d.js" "$@"
EOF
chmod +x staging/bin/eslint_d

# 打包
cd staging
tar -czf eslint_d-15.0.2-ohos-aarch64.tar.gz .
```

## 问题与方案

### 问题 1: npm pack 不包含依赖

**表现**: npm pack 创建的包只有 20KB，不包含 node_modules。

**根因**: npm pack 只打包源码，依赖需要通过 npm install 安装。

**方案**: 手动复制 node_modules 到预编译包中，创建包含所有依赖的 bundle。

### 问题 2: prepare 脚本失败

**表现**:
```
.git can't be found
sh: scripts/install-fixture-deps.sh: No such file or directory
```

**根因**: 从 npm registry 下载的 tarball 没有 .git 目录和 scripts/。

**方案**: 从 GitHub 克隆完整源码，包含所有文件。

### 问题 3: GitHub 克隆失败

**表现**: `fatal: unable to access: Empty reply from server`

**根因**: 网络问题，GitHub 连接不稳定。

**方案**: 使用 GitHub 加速代理 `https://gh-proxy.com/https://github.com/...`

## 验证结果

```bash
# 验证源码编译
node bin/eslint_d.js --version
# 输出: eslint_d: v15.0.2, bundled eslint: v10.0.3

# 验证预编译包
cd ~/usr/local
node lib/node_modules/eslint_d/bin/eslint_d.js --version
# 输出: eslint_d: v15.0.2, bundled eslint: v10.0.3
```

## 交付物

### 预编译包

- **文件**: `eslint_d-15.0.2-ohos-aarch64.tar.gz`
- **大小**: 93 MB
- **路径**: `archives/e/eslint_d/15.0.2/packaging/eslint_d-15.0.2-ohos-aarch64.tar.gz`
- **类型**: Node.js bundle（包含所有依赖）

### 包内容

```
lib/
  node_modules/
    eslint_d/
      package.json
      bin/eslint_d.js
      bin/eslint.js
      lib/
        commands.js
        config.js
        daemon.js
        forwarder.js
        hash.js
        help.js
        launcher.js
        miss.js
        resolver.js
        service.js
        status.js
        version.js
      node_modules/
        debug/
        eslint/
        supports-color/
        ... (268 packages)
bin/
  eslint_d              # 入口脚本
```

### 安装方式

```bash
# 从预编译包安装
tar -xzf eslint_d-15.0.2-ohos-aarch64.tar.gz -C ~/usr/local
cd ~/usr/local
node lib/node_modules/eslint_d/bin/eslint_d.js --version

# 或者通过启动脚本
~/usr/local/bin/eslint_d --version
```

## 注意事项

1. **Node.js 应用无 ELF 签名**: 不适用传统质量门禁（G0-G4）
2. **预编译包包含所有依赖**: 用户无需 npm install
3. **依赖 Node.js 运行时**: 用户需要安装 Node.js >= 22
4. **启动脚本**: 需要正确设置 NODE_PATH

## 编译状态

**最终状态**: published

- ✅ 源码克隆成功
- ✅ npm install 成功
- ✅ 测试通过（114 passing）
- ✅ 版本验证成功（15.0.2）
- ✅ Bundle 打包成功（包含所有依赖）
- ✅ Bundle 验证成功（--version 输出正确）
- ✅ 归档文件创建完成
- ✅ 预编译包路径: `archives/e/eslint_d/15.0.2/packaging/eslint_d-15.0.2-ohos-aarch64.tar.gz`

**特殊情况说明**:
- Node.js 应用无 ELF 签名（不适用传统 G0-G4 质量门禁）
- Bundle 包含所有依赖，用户无需 npm install
- 需要使用 GitHub 加速代理克隆源码
**产物路径**: archives/e/eslint_d/15.0.2/packaging/eslint_d-15.0.2-ohos-aarch64.tar.gz
**门禁结果**: Node.js 应用不适用传统 G0-G4 门禁（G0-G4: skipped）
---

**编译结束**: 2026-06-05 11:50
**最终状态**: built
