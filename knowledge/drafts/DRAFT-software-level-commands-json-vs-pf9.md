# DRAFT-software-level-commands-json-vs-pf9 — 软件级 commands.json 与 PF9 的冲突

## 可复现症状与稳定错误签名

对**任何**新增了**软件级** `commands.json` 的包（即
`archives/<字母>/<包名>/commands.json`，4 段路径）跑仓库前端硬闸：

```
✗ PF9 分支/路径闸: 变更路径缺版本目录层（须 archives/<字母>/<包>/<版本>/<文件>）
   ——CI 将报 No packages to build（490 例）: archives/c/cython/commands.json
```
稳定特征：报错路径恰为 `archives/<字母>/<包>/commands.json`（**无版本段**）。

## 根因与最小复现

**两侧规则的真实口径（均已读源码确证）**：

1. **CI 的 L0k（权威，决定 CI 是否失败）**
   `ci/conan/build_and_test.sh`：
   ```bash
   CONANFILE_DIR="$(dirname "$CONANFILE")"      # .../<包>/<版本>
   PKG_SOFTWARE_DIR="$(dirname "$CONANFILE_DIR")"   # .../<包>
   COMMANDS_JSON="${PKG_SOFTWARE_DIR}/commands.json"
   ```
   → **必须在软件级**（`archives/<字母>/<包>/commands.json`）。
   知识库条目 **E424** 亦明确："保持在软件级目录而不是版本目录"。
   仓内**软件级共 3156 个**，版本级仅 16 个。

2. **`scripts/ohc/preflight.py` 的 PF9（本地硬闸）**
   ```python
   arch = [f for f in files if f.startswith("archives/")]
   bad = [f for f in arch if len(f.split("/")) < 5]   # 4 段即命中
   ```
   → 软件级路径只有 4 段，**必然命中**。

**最小复现（证明这是系统性误报，而非本包缺陷）**：
```bash
# 对仓内**已合并**的同类提交跑同一 preflight
S=$(git log --diff-filter=A --format=%H -1 origin/main -- archives/l/lsd2/commands.json)
python3 scripts/ohc/preflight.py . "${S}^" "$S"
# -> ✗ PF9 ... archives/l/lsd2/commands.json   （与新增该文件的包完全相同的报错）
```

## 已尝试方案（含失败方案及结果）

| 方案 | 结果 |
|---|---|
| 把 `commands.json` 挪到**版本级**（`archives/c/cython/3.3.0/commands.json`，5 段） | PF9 通过，但 **PF8 立刻失败**："CLI 包（application/bindirs 非空）缺 commands.json——R38 必拦"；且 CI L0k 也会失败（它只看软件级）→ **本末倒置** |
| 两级**同时**放（软件级 + 版本级） | PF9 仍报错（软件级那份依旧 4 段）；且制造冗余文件 → 不采用 |
| 保留软件级，PF9 该条按已知误报处理 | **采用** |

## 最终方案、输入输出与真实验证

**方案**：**保留软件级** `commands.json`（满足 CI L0k 与 E424 的权威口径）。
- PF8 对软件级布局**通过**（实测：6 个包 preflight 问题数均为 0，
  其中 cython 含 CLI，仅 PF9 报这一条且为误报）；
- 建 PR 时该条按已知误报处理（`--no-preflight` 显式跳过，或在 PR 说明中注明）；
- **不要**为过 PF9 而迁移层级——那会让 CI L0k 失败。

**真实验证**：
```
# cython（含 CLI，软件级 commands.json）
$ python3 scripts/ohc/preflight.py . origin/main HEAD
✗ PF9 ... archives/c/cython/commands.json          <- 唯一一条，已确证为误报
# 对照：已合并的 lsd2 新增软件级 commands.json 的提交，报完全相同的 PF9
```

## 注意事项

1. **判据优先级**：CI 的 L0k > 本地 PF9。前者决定 CI 成败，后者是"提交前形态"
   检查；两者冲突时以 CI 为准并用 `--no-preflight` 说明。
2. **不要为了过本地闸而破坏 CI 契约**——层级迁移会使 L0k 直接失败。
3. PF8（要求软件级有）与 PF9（要求 ≥5 段）在软件级 `commands.json` 上
   **天然冲突**；本仓既有 3156 个软件级实例都处于该误报下，
   说明这是闸门实现问题，宜从 `preflight.py` 侧加
   "软件级 `commands.json` 豁免"（`archives/<字母>/<包>/commands.json` 白名单）。
