# e2b homebrew — 编译笔记

## 基本信息
- 软件: e2b (E2B CLI)
- 版本: 2.12.2
- 构建日期: 2026-06-21
- 构建系统: npm (Node.js)
- 平台: OpenHarmony aarch64

## 编译过程

### 源码获取
- e2b CLI 实际是 npm 包 `@e2b/cli`，非 Go 项目
- 从 `https://registry.npmjs.org/@e2b/cli/-/cli-2.12.2.tgz` 下载
- GitHub 仓库 `e2b-dev/e2b` 的 `packages/cli` 子目录是 TypeScript 源码
- npm 包已包含预构建的 `dist/index.js`（2.6MB bundled JavaScript）

### 安装方法
1. 使用 `npm install -g --prefix $TEST_PREFIX$DEFAULT_PREFIX .` 全局安装
2. npm 创建符号链接 `bin/e2b -> ../lib/node_modules/@e2b/cli/dist/index.js`
3. 替换符号链接为实际文件（避免 packaging 管线问题）

### 平台适配
1. **Shebang 修复**: `#!/bin/env -S node --enable-source-maps` → `#!/data/service/hnp/bin/node --enable-source-maps`
   - 原因: OpenHarmony 的 toybox `env` 不支持 `-S` 参数
2. **符号链接解析**: npm 全局安装创建的符号链接指向临时目录，需替换为实际文件
3. **Node.js 依赖**: 运行时依赖 Node.js（已预装 v24.13.0）

### 验证
- `e2b --version` → `2.12.2` ✅
- `e2b --help` → 显示完整帮助 ✅
- `e2b auth info` → `Not logged in` ✅ (匹配 Homebrew formula 测试)

## 知识提取
1. e2b CLI 是 Node.js 应用，非 Go 项目（任务描述有误）
2. `#!/bin/env -S` shebang 在 OpenHarmony 不可用，需替换为绝对路径
3. npm 全局安装的符号链接链需解析为实际文件才能通过质量门禁

## 编译结束
**最终状态**: built
**打包产物**: e2b-homebrew-ohos-aarch64.tar.gz (12109KB)
**质量门禁**: PASS (G1-G4 全通过，有警告但无失败)
---

**编译结束**: 2026-06-21 19:39
**最终状态**: published
