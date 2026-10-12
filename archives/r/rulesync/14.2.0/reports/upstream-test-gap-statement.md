# 上游测试执行说明（rulesync 14.2.0）

> **状态更新（2026-10-01）：缺口已关闭** —— 上游 345 个测试文件（8176 用例）**已在本机真实执行**，
> 结果与失败原因见 `reports/upstream-test-results.md`。本文件保留为"问题→解决"的过程记录。

## 结果速览

| 套件 | 文件数 | 用例总数 | 通过 | 失败 | 跳过 | 通过率 |
|---|---|---|---|---|---|---|
| 单元（`pnpm test`） | 329 | 7456 | 7448 | 8 | 0 | 99.89% |
| E2E（`pnpm test:e2e`） | 16 | 720 | 719 | 1 | 0 | 99.86% |
| **合计** | **345** | **8176** | **8167** | **9** | **0** | **99.89%** |

**测试用例零改动**；9 项失败均为平台/环境约束（上游自更新二进制的平台矩阵 6、HMDFS 文件系统语义 1、缺 Bun 运行时 1、环境相关 1）。

## 曾经的阻塞与解决

| 阶段 | 现象 | 处置 |
|---|---|---|
| 初始 | 上游默认运行器 `vitest 4.1.10 + vite 8.1.4` 需要 rolldown 原生 N-API 绑定；在本 HMDFS 工作区 dlopen 被拒（`ERR_DLOPEN_FAILED: Permission denied`，签发后仍拒） | 判定为平台边界；先以 test_package + W3 提供替代验证 |
| 探索 | `node:wasi` 回退不可用（最小 `new WASI(...)` 即 `uvwasi_init` → `UVWASI_EBADF`）；bun 无 OHOS 构建；其它可写挂载点全部 dlopen 受限 | 逐一排除并留证（见知识草稿 `DRAFT-rulesync-napi-dlopen-denied`） |
| 解决 | 改为 **vitest 3.2.7 + vite 7.3.7**（esbuild 以子进程执行，不受 dlopen 限制）+ **`rollup` → `@rollup/wasm-node@4.59.0`**（pnpm overrides，官方纯 WASM 实现） | 单元 7456 + E2E 720 全部真实执行 ✅ |

## 复现命令

```bash
pnpm add -D vitest@3 vite@7
# pnpm-workspace.yaml → overrides: { rollup: npm:@rollup/wasm-node@4.59.0 }
pnpm install --ignore-scripts --no-frozen-lockfile

node node_modules/vitest/vitest.mjs run --silent=true --reporter=json --outputFile=unit-results.json

mkdir -p dist-bun   # E2E 要求 RULESYNC_CMD 形如 dist-bun/rulesync-<platform>-<arch>
printf '#!/bin/sh\nset -eu\nexec node "%s/dist/cli/index.js" "$@"\n' "$PWD" > dist-bun/rulesync-ohos-arm64
chmod 755 dist-bun/rulesync-ohos-arm64
RULESYNC_CMD=dist-bun/rulesync-ohos-arm64 \
  node node_modules/vitest/vitest.mjs run --config vitest.e2e.config.ts
```

## 与 Conan 适配的关系

- 上游套件验证源码行为；`test_package`（8 项断言，含 2 项鸿蒙特有）与 W3 本地 CI 模拟验证**打包产物**的消费路径，两者互补。
- Conan 包层面：`conan create` / `conan-verify`（G0–G4 + L2/L4/L5）/ W3 全绿，`.ci-result.json` 由 `finish` 生成（`exit_code: 0`，`log_sha256` 与 `reports/w3-local-ci.log` 一致）。
