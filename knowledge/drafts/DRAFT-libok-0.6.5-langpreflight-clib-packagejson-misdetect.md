# DRAFT-libok-0.6.5-langpreflight-clib-packagejson-misdetect

> Contributor: pc2-16 | Status: Draft | Updated: 2026-09-19
> Source: libok 0.6.5 HarmonyOS PC 适配（task libok-0.6.5-r01-pc2-16-20260919T124957Z，lang-preflight 阶段）
> 领域：语言预检（R47 / lang_detect）/ 构建系统识别

## 背景

libok 0.6.5 是 jwerle 的纯 C TAP 输出库（`ok_expect/ok/notok/ok_done`，构建系统为
顶层 Makefile，clib.json 声明 `src: [ok.h, ok.c, Makefile]`，源码 100% C）。但
`ohc-run.py lang-preflight libok 0.6.5 --src ...` 判定
`detected_language=mixed（build_system=npm）`，并自动写入 env_unsupported 终态。

上游仓库顶层存在 package.json，但其全部内容仅为 npm/clib 双生态发布元数据：
`"scripts": { "version": "./scripts/update-clib-json && git add clib.json" }`——
`update-clib-json` 是一个 node 脚本，只在打 tag 时把 clib.json 的 version 字段
同步为 package.json 的版本号，与构建/测试无关。

## 错误签名

```text
lang-preflight.*detected_language.*mixed|build_system.*npm|
package.json 含 main/scripts/engines/bin|任务标记 cpp，实测源码为 mixed（npm）
```

## 根因

`scripts/ohc/lang_detect.py::_manifest_scan` 对 package.json 的判定条件过宽：

```python
pj = tops.get("package.json")
if pj is not None:
    head = _read_head(pj)
    if any(k in head for k in ('"main"', '"scripts"', '"engines"', '"bin"')):
        return ("nodejs", "npm", _clip("package.json 含 main/scripts/engines/bin"))
```

libok 的 package.json 含 `"scripts"` 键（发布辅助脚本），命中条件 → manifest 判为
nodejs/npm。随后 `_source_stats` 统计源码 100% c → §4.7 冲突规则
（manifest=nodejs vs 统计 c 占 100%）→ `detected_language=mixed` → 与任务默认语言
cpp 不匹配 → 自动写终态 env_unsupported。

两个结构性问题叠加：
1. **判定条件过宽**：`"scripts"` 键存在即判 nodejs，未区分"应用脚本"与"发布辅助脚本"；
2. **检查顺序**：package.json 检查排在顶层 Makefile 之前，clib 生态 C 库的
   clib.json（真正的包元数据，声明 C 源码）完全没有参与判定。

## 解决方案（本轮实证）

按 R47 边界规则"辅助脚本不算主体"（协议 §D.4）+ c↔cpp 兼容族人工复核：
- 顶层存在 Makefile（构建系统 make）；
- clib.json 声明 src=[ok.h, ok.c, Makefile]（clib 生态的权威包元数据）；
- 源码统计 100% c（ok.c/test.c 两个 C 源文件）。

→ 真实语言判为 c（与任务默认 cpp 属兼容族），覆盖 env_unsupported 误判，继续完成
适配（make 编译、上游测试 exit 0、conan create 通过、test_package 消费者测试通过），
最终以真实 result（同 task_id）覆盖误判产物。

## 验证

- 误判命令与输出：`ohc-run.py lang-preflight libok 0.6.5 --src ...` →
  `detected_language: mixed`、`build_system: npm`（日志留档）；
- 人工复核：`cat package.json`（仅 version 脚本）、`cat clib.json`（src 全 C）、
  `make all` 直接编译通过（clang 15，libok.a + libok.so.0.6）；
- 上游测试：`./ok-test` → TAP version 14 / 1..4 / 1..2，exit 0；
- Conan：`conan create`（G2）通过，test_package 消费者测试通过。

## 适用边界

- 适用：clib/npm 双生态发布的 C/C++ 库（package.json 含任意 "scripts" 键，
  顶层有 Makefile/CMakeLists 且源码统计 ≥70% C/C++）；
- 反例：package.json 含真实应用入口（main/bin 指向 JS 实现）或 npm 构建脚本的
  Node 包——此时判 nodejs 正确；
- 处理动作：误判触发时按上述规则人工复核后覆盖终态继续适配，不要静默接受
  env_unsupported，也不要在 result 中伪造语言字段（如实记录判定证据）。

## 查重差异

- `exact_duplicate`：false（index.tsv / doc / drafts 均无 libok/package.json 条目）；
- `causal_duplicate`：false（与 emio cargo / debugbreak gnumakefile 草稿同类
  `_manifest_scan` 误判族，但触发点分别为辅助 Cargo.toml、GNUmakefile+辅助 .py，
  本条目为 package.json "scripts" 键 + clib/npm 元数据层，触发机制不同）；
- `trigger_overlap`：partial（三者都源于 lang_detect 判定路径，但触发器不同）；
- `solution_overlap`：partial（复用 manual-boundary-rule-override 思路，本条目新增
  clib.json 作为权威包元数据的复核要点）；
- `combination_novelty`：true（clib/npm 元数据 → nodejs 误判的组合未见既有条目）；
- `boundary_novelty`：true（补充 package.json "scripts" 发布辅助脚本的判定边界）；
- `test_migration_novelty`：false（不涉及测试迁移）。
