# actions-up 1.16.0 HarmonyOS PC 适配说明

## 软件说明

actions-up 是一个 Node.js CLI，用于扫描并更新 GitHub Actions 引用，支持 SHA pinning、保留 ref、dry-run 和 JSON 输出等功能。

## 适配方式

本次适配使用上游官方 npm 发布产物 `actions-up@1.16.0`。该发布产物已经包含 `bin/actions-up.js`、`dist/`、`package.json`、`license.md` 和 `readme.md`。

HarmonyOS PC 构建阶段仅安装 production runtime dependencies。最终 Conan 包提供 `bin/actions-up` 启动脚本，并通过系统 Node.js 运行打包后的 JavaScript CLI。

## 上游测试说明

上游源码包含 62 个 Vitest 测试文件，共 557 个测试用例。

上游默认开发依赖使用 Vite 8 / Rolldown。在当前 HarmonyOS PC Node.js 环境中，Rolldown 原生 OpenHarmony ARM64 addon 无法通过 process.dlopen() 加载，WASI fallback 也受到运行环境限制。

因此仅对测试运行环境进行兼容性调整，不修改任何上游测试源码：

1. Vitest 保持 4.1.9。
2. 测试环境将 Vite 调整为 7.3.6。
3. Rollup 使用 @rollup/wasm-node 4.60.1，避免加载原生 addon。
4. 上游 test:unit 脚本保持原有 vitest --run --coverage 不变。

HarmonyOS PC 实际执行结果：

- Test Files: 62/62 passed
- Tests: 557/557 passed
- 测试通过率: 100%
- Statements Coverage: 100%
- Branches Coverage: 100%
- Functions Coverage: 100%
- Lines Coverage: 100%

未修改、删除或跳过任何上游测试用例。

运行时本身不依赖 Vite、Vitest、Rolldown 或 Rollup。官方 npm 发布产物已经包含构建完成的 dist/。

## test_package
新增 3 项消费者侧验证：

1. 验证 Conan Runtime Environment 中可以找到 actions-up 命令
2. actions-up --version 输出包含 actions-up/1.16.0
3. actions-up --help 输出包含 Usage:

## 验证命令

`python3 scripts/ohc-run.py conan-verify actions-up 1.16.0`
