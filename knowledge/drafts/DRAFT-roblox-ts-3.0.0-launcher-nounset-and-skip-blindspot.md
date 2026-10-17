# DRAFT-roblox-ts-3.0.0-launcher-nounset-and-skip-blindspot

> Contributor: OpenDesk Agent | Status: Draft | Updated: 2026-09-30
> Source: roblox-ts 3.0.0 HarmonyOS PC 适配（CI build **#65252** 实测失败 → 修复）
> 领域：配方自生成脚本（launcher/wrapper）/ test_package 门禁有效性

## 问题

PR #13937 的 CI 在 `conan-build-test` 失败，`test_package` 报 **3 条 FAIL**：

```
[FAIL] rbxtsc --version output (.../p/bin/rbxtsc[16]: RBXTSC_NODE: parameter not set)
[FAIL] rbxtsc --help CLI surface
[FAIL] [OHOS] launcher output with unusable first-on-PATH node (... RBXTSC_NODE: parameter not set)
=== Results: 28 passed, 3 failed, 0 skipped ===
```

同一份配方在本机 `conan create` **exit 0**，且只报 `27 passed / 5 skipped` —— 缺陷被漏检。

## 根因（两段）

**① 启动器模板：`set -u` + 裸引可能未设置的变量**

生成出的 `bin/rbxtsc` 第 3 行是 `set -eu`，第 16 行是：

```sh
for cand in "$RBXTSC_NODE" "$(command -v node 2>/dev/null)" /data/service/hnp/bin/node; do
    [ -n "$cand" ] || continue      # ← 来不及执行：展开阶段就已中止
```

POSIX shell 在 `-u`（nounset）下展开**未设置**变量即终止脚本。本机最小复现：

```sh
$ printf '#!/bin/sh\nset -eu\nfor c in "$RBXTSC_NODE" x; do echo "$c"; done\n' > t.sh
$ unset RBXTSC_NODE; /bin/sh t.sh
t.sh[3]: RBXTSC_NODE: parameter not set      # RC=1
```

启动器的原意是「`RBXTSC_NODE` 可选覆盖」，语义上就该是 `${RBXTSC_NODE:-}`。

**② 本地门禁漏检：运行期用例被整体 `[skip]`**

本机 conan 派生 node 进程不稳定（E400 + 沙箱限制），test.sh 的 node 门槛探测失败，
于是 `if [ -n "$NODE_BIN" ] … else skipped "rbxtsc CLI execution (no working node interpreter)" fi`
整块跳过 —— 4 条断言只用**一条** skip 概括，`[OHOS]` 运行期启动器用例同样 skip。
**启动器的运行路径在本地从未被执行**，缺陷只在 CI（node 可用）暴露。

> 同类盲区：本包此前还出现过「PR 内 5 处计数声明与实测不一致」（20 vs 28），
> 根因之一也是 skip 语义把多个断言位折叠成一条，使口径难以核对。

## 解决方案（已在本包落地）

1. **生成脚本一律用默认值展开**：
   ```sh
   for cand in "${RBXTSC_NODE:-}" "$(command -v node 2>/dev/null)" /data/service/hnp/bin/node; do
   ```
   （保留 `set -eu` 的 fail-fast 价值，仅修展开写法。）
2. **逐条 skip**：CLI 分支的 `else` 改为 4 条独立 `skipped "… (no working node interpreter)"`，
   使**断言位总数与环境无关**（本包恒定 32 = 19 完整性 + 3 sha256 + 4 CLI + 6 `[OHOS]`）。
   本地 27/0/5、CI 应 32/32，分母一致，杜绝计数漂移。
3. **补不依赖运行时的静态守卫断言**（`[OHOS] 6`）：
   ```sh
   if grep -q '${RBXTSC_NODE:-' "$D/rbxtsc" && ! grep -q '"$RBXTSC_NODE"' "$D/rbxtsc"; then
       ok "[OHOS] launcher expands unset RBXTSC_NODE safely (\${RBXTSC_NODE:-})"
   else
       bad "[OHOS] launcher uses bare \$RBXTSC_NODE under set -u"
   fi
   ```
   该断言在 node 不可用的机器上照样执行 —— 直击本缺陷。
4. 生成后先 `sh -n <launcher>` 做语法检查（注意：`sh -n` 抓不到 nounset 运行期错误，
   故 3 才是关键守卫）。

## 验证

- 本机最小复现：裸引写法 `RC=1 / RBXTSC_NODE: parameter not set`；`${…:-}` 写法 `RC=0`；
- 修复后启动器回归 **4/4**（`unset RBXTSC_NODE`、`unset + PATH 首位坏 node`、`RBXTSC_NODE` 显式覆盖、无参数调用）→ 均输出 `3.0.0`、`RC=0`；
- 修复后 `conan create` → **exit 0**（`27 passed, 0 failed, 5 skipped`）；
- CI 侧：修复提交后 `/rebuild` 复跑，`[OHOS]` 三条对应的运行期断言转为通过（见 PR #13937 后续 CI 评论）。

## 适用边界

- 适用：任何**自生成** shell 启动器/wrapper 的配方（npm CLI、脚本工具、header-only 工具），
  以及任何「运行期依赖外部工具链且该工具链在部分环境不可用」的 test_package。
- 反例：直接复用上游自带脚本且不改写的配方 —— 上游脚本的 nounset 行为属上游责任，
  但同样建议在 test 层用「变量未设置」场景覆盖一次。
- 关键提醒：**本机绿灯 ≠ 环境无关绿灯**。凡「因外部工具链缺失而 skip」的用例，
  都必须配一条同语义的、不依赖该工具链的静态/结构断言。

## 查重差异

- `exact_duplicate`：false（drafts/index.tsv 无 set -u / launcher nounset 条目）。
- `causal_duplicate`：false（与 E400 的运行时能力问题正交：本条是配方自生成脚本的写作缺陷 + 门禁有效性）。
- `trigger_overlap`：partial（同属 npm/Node CLI 适配场景，但触发点为「启动器执行」而非「node 能否运行」）。
- `solution_overlap`：partial（同样落到 test_package 断言设计，但新增「逐条 skip 保计数恒定 + 运行时无关静态守卫」两点）。
- `combination_novelty`：true（`set -u` 展开缺陷 × 「skip 导致的本地漏检」组合未见既有条目）。
