# 测试报告 — roblox-ts 3.0.0（npm / Node.js CLI）

> **项目**: roblox-ts（TypeScript → Luau 编译器，入口 `rbxtsc`）
> **测试日期**: 2026-09-29
> **测试环境**: HarmonyOS PC，HongMeng Kernel 1.12.0 aarch64（node v24.13.0 / npm 11.6.2）
> **测试类型**: 上游官方测试套件（mocha 单元层）+ conan test_package 消费者测试 + 端到端编译验证

---

## 一、测试摘要

### 1.1 conan test_package（消费者层，`conan create` 内执行）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 断言总数 | 32 | 100% |
| 通过 (PASS) | 27 | 84.4% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 5 | 15.6% |

**核心功能通过率**: ✅ **100%（27/27 已执行断言）**

> 断言位总数**恒为 32**（与 node 可用性无关，`[skip]` 逐条计数），构成为
> 19 打包完整性 + 3 sha256 逐字节一致 + 4 CLI 运行期 + 6 `[OHOS]` 鸿蒙专项。
> 本机 5 项 SKIP = CLI 运行期 4 条 + `[OHOS]` node 门槛 1 条（本机 `conan create`
> 派生的 node 进程无法稳定启动，见 §2.4）；其余 27 项全部通过。
> **CI（node 可用）应 32/32 全执行。**

> **CI 首轮实测（build #65252）**：`28 passed, 3 failed, 0 skipped` —— 失败 3 项
> 全部指向启动器缺陷 `RBXTSC_NODE: parameter not set`（本机因 SKIP 未覆盖该路径，
> 详见 §2.4 第 3 条）。修复后本机复跑为 **27 passed / 0 failed / 5 skipped**。

### 1.2 上游官方测试（mocha 单元层）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 用例总数 | 131 | 100% |
| 通过 (PASS) | 131 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**上游用例通过率**: ✅ **131/131 = 100%**

测试命令：`npm ci && npm run build && ./node_modules/.bin/mocha --timeout 0 --recursive out/CLI/test.js --reporter spec`
（= 上游 `scripts.test-compile`），实测 `131 passing (9s)`，exit 0。
用例逐项名称见 `reports/upstream-unit-test-names.txt`，完整输出见 `reports/upstream-mocha.log`。
组成：include/non-compiled 拷贝 2 + diagnostic 用例 85 + 源文件编译用例 44。

### 1.3 上游集成测试（rojo + lune）

| 指标 | 数值 |
|:----:|:----:|
| spec 文件 | 38 |
| `it()` 用例（grep 统计，含 .tsx） | 462 |
| 实际执行 | ❌ 0（环境缺 Rust 工具链） |

上游 `npm test` 的后两级 `test-rojo` / `test-run` 需 foreman 分发的 Rust 外部二进制
（`rojo=7.4.4`、`lune=0.8.8`、`run-in-roblox=0.3.0`）。目标环境无 Rust 工具链，
conan 制品仓与 cmd-pkgs 均无对应制品（`conan download rojo|lune -r=ohpcd` exit 1）
→ 按 R51 如实申报「未执行」，不虚报通过率。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**：可执行的全部测试层（conan 消费者层 + 上游 mocha 单元层）100% 通过；
端到端 TypeScript→Luau 编译实测产出正确 Luau。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 上游集成层（rojo + lune）缺 Rust 工具链 | 38 个 spec / 462 个 it() 未执行 | 🟡 |
| 本机 conan 派生 node 进程不稳定（E400 + 沙箱） | test_package 中 5 项运行期断言 skip | 🟡 |
| 启动器 `set -u` 裸引未设变量（CI 首轮暴露，已修复） | CI 3 条断言失败；已修复并加运行时无关守卫 | 🟢 已解决 |

### 2.3 可用功能清单

```
✅ rbxtsc --version                → 3.0.0
✅ rbxtsc --help                   → 完整 yargs 选项表（--project/--watch/--luau/--rojo …）
✅ TypeScript → Luau 端到端编译      → out/main.server.luau 内容正确
✅ 非法工程路径报错退出（非 0）        → 编译器管线真实运行
✅ Luau 运行时随包分发               → include/Promise.lua、include/RuntimeLib.lua
✅ 运行时依赖闭包随包分发             → node_modules（9 直接依赖 + 传递依赖，共 51 包）
⚠️ rbxtsc 运行期执行（本机 conan 环境内）→ 环境受限，见 2.4
❌ 上游集成测试（rojo/lune）          → 需 Rust 外部二进制，目标环境不可用
```

### 2.4 已知限制

1. 上游集成测试层（`test-rojo` / `test-run`）需要 `rojo`/`lune` 两个 Rust 二进制，
   目标环境无 Rust 工具链（CI 能力矩阵 Rust ❌），制品仓亦无对应包 → 无法执行。
2. 本机 `conan create` 派生的 node 进程存在环境性不稳定：node 正常 JIT 执行 JS 即崩
   （知识库 E400，`Check failed: 12 == (*__errno_location())`，rc=133；`--jitless` 恢复），
   叠加沙箱对「conan 派生进程建软链接」的限制（`npm install` 在 `node_modules/.bin`
   报 `EACCES symlink`）。配方已按 E400 与 actions-up 范式做三重加固
   （`NODE_OPTIONS=--jitless` + `--no-bin-links` + `env=None`），`build()` 阶段实测通过；
   但 `test_package` 阶段由 conan 直接派生的 node 仍可能异常终止，故该类断言按
   环境 skip（与 `archives/l/leaflet-markercluster` 同款约定）。同机对照实验显示
   已并入 main 的 `archives/a/acorn` 强制重建在同一位置同样 SIGABRT。
3. `--no-bin-links` 使包内无 `node_modules/.bin`；`rbxtsc` 运行期直接 `require`
   模块，不依赖 `.bin`，功能不受影响。
4. **启动器 `set -u` 缺陷（CI 首轮暴露 → 已修复）**：首轮 CI（build #65252）报 3 条 FAIL —
   `/pkg/bin/rbxtsc[16]: RBXTSC_NODE: parameter not set`。根因为生成脚本写了 `set -eu`
   却**裸引**未设的 `$RBXTSC_NODE`（POSIX nounset 在展开处即中止）；本机因 node 不可用、
   运行期用例整体 `[skip]` 而**漏检**。修复：启动器改用 `${RBXTSC_NODE:-}`；CLI 分支改为
   **逐条 skip**（断言位总数恒定 32）；新增**不依赖 node** 的静态守卫用例 `[OHOS]` 5。
   修复后本机回归 4/4（RBXTSC_NODE 未设 / 未设+PATH 首位坏 node / 显式覆盖 / 无参数调用
   → 均 `3.0.0`、RC=0），`conan create` exit 0。

---

## 三、端到端编译验证（真实产物）

```bash
$ node --jitless out/CLI/cli.js --type package -p <smoke-project>
$ cat out/main.server.luau
-- Compiled with roblox-ts v3.0.0
local answer = 42
local function add(a, b)
	return a + b
end
local acc = 0
for i = 0, 9 do
	acc = add(acc, i)
end
print(acc)
return {
	add = add,
	answer = answer,
}
```

同时验证了「安装产物与 npm dist 逐字节一致」：`out/CLI/cli.js`、
`out/CLI/index.js`、`include/RuntimeLib.lua` 的 sha256 与官方 tarball 完全相同。

---

## 四、鸿蒙特有用例（断言位 6 = 5 条始终执行并通过 + 1 条需 node 运行时门槛）

> 计数口径（全文件统一）：`ohos_specific_test_count = 5` 指**始终执行并通过**的鸿蒙特有断言；
> 第 6 行为 node 门槛项，本机环境性 skip（详见 §2.4）。

| # | 用例 | 结果 |
|---|------|------|
| 1 | `bin/rbxtsc` 为 POSIX sh 包装（不依赖上游 `#!/usr/bin/env node`） | ✅ |
| 2 | 启动器显式解析解释器候选（RBXTSC_NODE > PATH > OHOS hnp node） | ✅ |
| 3 | 启动器以 `node --jitless` 运行（OHOS V8 JIT 规避，E400） | ✅ |
| 4 | 启动器使用 `exec`（conan 缓存跨 UID 物化后可经 /system/bin/sh 执行） | ✅ |
| 5 | 启动器在 `set -u` 下安全展开未设的 `RBXTSC_NODE`（`${RBXTSC_NODE:-}`；CI #65252 回归项，不依赖 node） | ✅ |
| 6 | 运行期：PATH 首位为不可用 node 时启动器仍解析出可用解释器（需 node，环境受限时 skip） | ⏭️ |

---

## 五、复现命令

```bash
# 1) 上游单测（从源码真实构建 + 131 用例）
curl -sSL -o src.tgz https://codeload.github.com/roblox-ts/roblox-ts/tar.gz/refs/tags/v3.0.0
tar -xzf src.tgz && cd roblox-ts-3.0.0
npm ci && npm run build
cd tests && npm install   # 见 notes.md §4 #2：需将 git+ssh 依赖替换为 registry 同版本
cd .. && ./node_modules/.bin/mocha --timeout 0 --recursive out/CLI/test.js --reporter spec

# 2) conan 配方（打包 + 消费者测试）
conan create archives/r/roblox-ts/3.0.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

# 3) 配方验证与收尾
python3 scripts/ohc-run.py conan-verify roblox-ts 3.0.0
python3 scripts/ohc-run.py finish roblox-ts 3.0.0 built
```
