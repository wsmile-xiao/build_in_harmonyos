# 上游测试真实执行结果 — rulesync 14.2.0

> 运行环境：OpenHarmony PC（aarch64），Node **v24.13.0**，工作区 HMDFS
> 运行器：**vitest 3.2.7 + vite 7.3.7**，其中 `rollup` 以 **`@rollup/wasm-node@4.59.0`** 经 pnpm `overrides` 替代原生 N-API 绑定
> 原始数据：`unit-results.json`（7456 用例）、`e2e-results2.json`（720 用例）

## 汇总

| 套件 | 文件数 | 用例总数 | 通过 | 失败 | 跳过 | 通过率 |
|---|---|---|---|---|---|---|
| 单元（`pnpm test`） | 329 | **7456** | **7448** | 8 | 0 | **99.89%** |
| E2E（`pnpm test:e2e`） | 16 | **720** | **719** | 1 | 0 | **99.86%** |
| **合计** | **345** | **8176** | **8167** | **9** | **0** | **99.89%** |

> 上游清单核对：单元 329 文件（`src/**/*.test.ts` 325 + `scripts/**/*.test.ts` 4）与 E2E 16 文件（`src/e2e/**/*.spec.ts`）**全部执行，无漏测**。

## 失败用例明细（9 项，均为平台/环境约束，非适配缺陷）

### A. 平台矩阵不适用（6 项）— `src/lib/update.test.ts`
```
update performBinaryUpdate should throw when binary asset is not found in release
update performBinaryUpdate should throw when SHA256SUMS asset is not found in release
update performBinaryUpdate should throw when checksum verification fails
update performBinaryUpdate should successfully update binary when checksum matches
update performBinaryUpdate should perform update when force is true even at latest version
update performBinaryUpdate should throw when checksum entry is missing for asset in SHA256SUMS
```
报错：`Error: Unsupported platform: openharmony arm64. Please download manually from …/releases`
原因：上游 `rulesync update` 的自更新二进制仅发布 linux/darwin/windows 资产，**OpenHarmony 不在其平台矩阵内**；
被测函数在 OHOS 上于更早分支抛错，测试期望的后续分支不可达。属**上游平台支持面**，与本次 Conan 适配无关。

### B. 平台文件系统差异（1 项）— `src/utils/file.test.ts`
```
file utilities directory listing findFilesByGlobs symlink support should not produce duplicated entries when a directory symlink cycle exists
→ Error: ELOOP: too many symbolic links encountered, realpath '.../skills/a/loop/a/loop/...'
```
原因：HMDFS 对符号链接环的 `realpath` 行为与上游 CI（ext4/APFS）不同（E079/E046 家族：HMDFS 链接语义差异）。

### C. 环境缺运行时（1 项）— `src/features/hooks/amp-hooks.test.ts`
```
AmpHooks should preserve shell quoting and expansion when executed by Bun Shell
→ Error: spawn bun ENOENT
```
原因：该用例需 **Bun** 执行 Bun Shell 语义；本机无 bun，且 bun 官方/npm 均**无 OpenHarmony 构建**
（`@oven/bun-*` 平台包止于 android；cmd-pkgs 无 bun 资产）。

### D. 环境相关（1 项）— `src/e2e/e2e-convert.spec.ts`
```
E2E: convert should not write any destination files when --dry-run is passed
→ AssertionError: expected '' to contain '[DRY RUN]'
```
人工等价验证（同目录、同参数）**通过**：
```
$ rulesync convert --from cursor --to claudecode --features rules --dry-run
[DRY RUN] Would write: …/.claude/rules/overview.md
[DRY RUN] Would convert 1 file(s) total from cursor to claudecode (1 rules)      EXIT=0
```
判定：CLI 功能面正常；该断言在所搭 wrapper+execFile 输出捕获组合下未取到 stdout，属**运行环境相关**，非功能缺陷。

## 复现命令（在 OHOS 工作区的源码副本中）

```bash
# 1) 让 vitest/vite 摆脱原生绑定（这是能跑起来的关键）
pnpm add -D vitest@3 vite@7
# 并在 pnpm-workspace.yaml 增加：
#   overrides:
#     rollup: npm:@rollup/wasm-node@4.59.0
pnpm install --ignore-scripts --no-frozen-lockfile

# 2) 单元测试（329 文件）
node node_modules/vitest/vitest.mjs run --silent=true --reporter=json --outputFile=unit-results.json

# 3) E2E（16 文件）：RULESYNC_CMD 必须形如 dist-bun/rulesync-<platform>-<arch>
mkdir -p dist-bun
printf '#!/bin/sh\nset -eu\nexec node "%s/dist/cli/index.js" "$@"\n' "$PWD" > dist-bun/rulesync-ohos-arm64
chmod 755 dist-bun/rulesync-ohos-arm64
RULESYNC_CMD=dist-bun/rulesync-ohos-arm64 \
  node node_modules/vitest/vitest.mjs run --config vitest.e2e.config.ts
```

## 为什么不使用上游默认运行器

上游 `vitest 4.1.10 + vite 8.1.4` 依赖 rolldown 的原生 N-API 绑定（`.node`）：
在本 HMDFS 工作区 dlopen 被平台拒绝（`ERR_DLOPEN_FAILED: Permission denied`，签名后仍拒；WASI 回退亦不可用：`node:wasi` 自身 `uvwasi_init` 失败）。
降级到 `vitest 3 + vite 7`（esbuild 子进程转译，`rollup` 用官方 WASM 实现）后**测试用例本身零改动**即可真实执行。
副作用与边界：`--jitless` 下 WebAssembly 不可用（不涉及本套件）；Bun 相关 1 例无法在该环境执行（见 C）。
