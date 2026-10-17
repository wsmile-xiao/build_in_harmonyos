# bruno-cli 3.4.2 适配笔记

## 编译环境
- 构建系统: npm
- 编译日期: 2026-09-18
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载 npm tarball: `npm pack @usebruno/cli@3.4.2`
2. 解压源码包
3. 运行 `npm install --ignore-scripts --no-audit --no-fund --no-package-lock --no-save` 安装依赖
4. 测试 CLI: `node --jitless bin/bru.js --version` → 输出 `3.4.2`
5. 创建 shell launcher 脚本 `bru`，使用 `node --jitless` 运行入口文件

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|

无 — 纯 JavaScript 包，无需原生编译，直接在 OHOS Node.js 运行时上工作。

## 源码修改

无补丁，无需修改源码。

## 依赖版本

- Node.js: v24.13.0 (OHOS)
- npm: 11.6.2 (OHOS)
- 365 个 npm 依赖包（运行时）

## 验证结果

```bash
$ node --jitless bin/bru.js --version
3.4.2

$ node --jitless bin/bru.js --help
Bru CLI 3.4.2
Usage: bru.js <command> [options]
Commands:
  bru.js import <type>   Import a collection from other formats
  bru.js run [paths...]  Run one or more requests/folders
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/bru | launcher | Shell launcher using `node --jitless` |
| res/bruno-cli/ | ~220KB+ | Source + node_modules |

## 注意事项

- 使用 `--jitless` 标志运行 Node.js，避免 JIT 在 OHOS 上的潜在问题
- npm 依赖在构建时安装并打包到 `res/bruno-cli/node_modules/`
- 包类型为 `application`（非 `library`），不设 `compiler` settings

## 重试修复（2026-09-18，第 2 次尝试）

上轮 PR #4044 CI 失败根因：worker 机器 OOM（`zsh:1: fork failed: out of memory`，
worker-prep/git-clone/cleanup 全挂），配方本身从未被 CI 执行过。本地复验通过。

本轮变更：

| # | 变更 | 原因 |
|---|------|------|
| 1 | settings 补全为 `os/arch/compiler/build_type` 四项 | PF8/L0p 配方静态闸（交叉编译矩阵前提），对齐 bootstrap/ai-cli 同类 npm 配方 |
| 2 | 新增 `validate()`：`settings.os not in ("Linux", "OHOS")` 抛错 | R32 平台判断规范，对齐 bootstrap 配方 |

复验：本地 W3 CI 模拟（setup.sh + build_and_test.sh）全绿——
L0/L1（含 R34 破坏性反向验证）/L2/L4/L5 全部 pass，`npm install` 365 依赖 1 分钟完成。
---

**编译结束**: 2026-09-18 18:45
**最终状态**: built
