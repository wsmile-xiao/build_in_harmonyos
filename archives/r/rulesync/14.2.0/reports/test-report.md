# 测试报告 — rulesync/14.2.0

生成时间：2026-10-01　|　归档：`archives/r/rulesync/14.2.0/`

## 1. conan create（真实执行，PASS）

```
$ conan create archives/r/rulesync/14.2.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
rulesync/14.2.0: RUN: npm install --ignore-scripts --omit=dev --no-audit --no-fund --no-package-lock --no-save --registry=https://registry.npmjs.org/
added 258 packages in 4m
rulesync/14.2.0: Package '6b129b068851896169fae42d399fa922d239ce8a' built
======== Launching test_package ========
rulesync/14.2.0 (test package): RUN: sh ".../test_package/test.sh" ".../p/bin/rulesync"
rulesync consumer tests passed
```
日志：`~/tmp/rulesync-adapt/30_conan_create_binfix.log`

## 2. test_package（8 项断言，含 2 项鸿蒙特有，PASS）

| # | 断言 | 类型 | 结果 |
|---|---|---|---|
| 1 | `rulesync --version` == `14.2.0` | 通用 | PASS |
| 2 | `--help` 含 `Unified AI rules management CLI tool` | 通用 | PASS |
| 3 | `--help` 含 `generate` | 通用 | PASS |
| 4 | `--help` 含 `import` | 通用 | PASS |
| 5 | launcher 含 `exec node --jitless` | **鸿蒙特有** | PASS |
| 6 | `node --jitless` 报告平台 `openharmony`（允许 `linux` 回退） | **鸿蒙特有** | PASS |
| 7 | `rulesync init` 生成 `rulesync.jsonc` + `.rulesync/rules/overview.md` | 通用 | PASS |
| 8 | `rulesync generate -t cursor -f rules` 生成非空 `.cursor/rules/overview.mdc` 且含 `Project Overview` | 通用 | PASS |

鸿蒙特有用例数 = **2（≥1 ✅）**

## 3. W3 本地 CI 模拟（PASS）

```
G0_RESULT=pass    KC_RESULT=pass    JC_RESULT=pass
L0_RESULT=pass    L1_RESULT=pass    L2_RESULT=pass    L4_RESULT=pass    L5_RESULT=pass
[ok] L1e: Negative test confirmed — test genuinely depends on rulesync
Build Summary: Total 1 / Success 1 / Pass rate 100.0% (1/1)
```
日志：`reports/w3-local-ci.log`；元数据：`ci-metadata.json`

## 4. 上游测试（**已真实执行**，规则见 `reports/upstream-test-results.md`）

| 套件 | 文件数 | 用例总数 | 通过 | 失败 | 跳过 | 通过率 |
|---|---|---|---|---|---|---|
| 单元（`pnpm test`） | 329 | **7456** | **7448** | 8 | 0 | **99.89%** |
| E2E（`pnpm test:e2e`） | 16 | **720** | **719** | 1 | 0 | **99.86%** |
| **合计** | **345** | **8176** | **8167** | **9** | **0** | **99.89%** |

- 运行器：**vitest 3.2.7 + vite 7.3.7**，`rollup` 以 **`@rollup/wasm-node@4.59.0`**（pnpm overrides）替代原生绑定；
  上游默认运行器（vitest 4 + vite 8 → rolldown）所需原生 N-API 绑定在本 HMDFS 工作区无法 dlopen（`ERR_DLOPEN_FAILED`，WASI 回退亦不可用）。
  **测试用例零改动**。
- 9 项失败均为平台/环境约束，非适配缺陷：平台矩阵不适用 6（`src/lib/update.test.ts`，上游自更新无 openharmony 资产）、
  平台文件系统差异 1（`src/utils/file.test.ts`，HMDFS realpath/符号链接环）、环境缺 Bun 1（`amp-hooks.test.ts`）、
  环境相关 1（`e2e-convert.spec.ts` dry-run stdout 断言，人工等价验证通过）。
- 原始数据：`unit-results.json`（7456 用例）、`e2e-results2.json`（720 用例）。

> test_package 的 8 项断言**不替代**上游测试统计（R51）；上表为上游套件真实执行结果。
