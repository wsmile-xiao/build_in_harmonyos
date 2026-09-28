# DRAFT-fabric-completion-conan-bare-version

## conan 2.29.1 export 阶段拒绝裸单段版本号：version="1" → Invalid package version

### 现象

真机（HarmonyOS PC，Conan 2.29.1）`conan-verify fabric-completion 1` G2 首验 FAIL：

```
ERROR: Invalid package version '1'
```

发生在 conan create 的 **export 阶段**，尚未进入下载/构建。真机最小复现：`version="1"` export 即拒绝；`version="1.0"` export 成功（`vt/1.0#...`）。

### 根因

- conan 2.x 版本引用校验要求版本号**至少 2 字符**（首字符 + 至少 1 个后续字符），`"1"` 长度不足
- 上游 fabric-completion 无 tag，版本号取 **Homebrew formula fabric-completion version=1**（公式允许裸 1）；「公式版本」口径与 conan 校验不兼容
- 官方 main 全部配方均为 X.Y 多段形式，无裸单段先例 → 归一化与本库惯例一致

### 推荐方案

版本号归一化为语义不变的多字符形式：

- `1` → `1.0`（Homebrew 版本 1 的 conan 合法形式）
- 同步归档目录名（archives/f/fabric-completion/1.0）、分支名（feat/fabric-completion-1.0，满足 L0n R40 精确匹配）、manifest/conanfile/test_package 全部版本引用
- manifest/notes 记录「任务卡版本 1 ↔ 包版本 1.0」映射

参考实现：`archives/f/fabric-completion/1.0/conanfile.py`（version 字段注释含真机实测说明）。

### 验证

```
修复前: conan create . → ERROR: Invalid package version '1'（export 阶段）
修复后: conan-verify fabric-completion 1.0 → G0-G4/L2/L4/L5 八门禁全绿（真机，Verdict: PASS）
```

### 关联

- 本任务 G2 FAIL 时知识图谱先后命中 E225/E540，均为**误报**——真实根因是版本号格式。教训：G2 FAIL 先看 conan-create.log 首行真实 ERROR，再采信知识图谱建议（详见 notes.md 真机实录）。
