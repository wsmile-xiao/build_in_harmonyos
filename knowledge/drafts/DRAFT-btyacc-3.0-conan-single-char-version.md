# Conan 2.29.1 拒绝单字符版本号 — btyacc 3.0 适配实证

- **草稿 ID**: DRAFT-btyacc-3.0-conan-single-char-version
- **来源**: btyacc 3.0 R01→R02（2026-09-05）；R01 任务版本号 "3" 在 conan-verify G2 被拒为真实首错，R02 版本号改为上游 "3.0" 后通过
- **分类**: conan / versioning / naming / packaging / slug
- **状态**: 本地草稿（未创建正式 E 条目、未写 index.tsv、未创建 Issue/PR 知识条目）

## 问题 / 错误签名

- conan create / conan export 在 "Exporting recipe to the cache" 阶段报：
  `ERROR: Invalid package version '3'`
- 复现命令（实证于 btyacc R01）：
  `conan create <archive>/b/btyacc/3 2>&1 | grep "Invalid package version"` → 命中
- 同版本号改为 "3.0" 后同一命令通过（btyacc R02 实证）。

## 根因

Conan 2.29.1 `conan/api/model/refs.py:148-154` 的 `RecipeReference.validate_ref()`：

```python
validation_pattern = re.compile(r"^[a-z0-9_][a-z0-9_+.-]{1,100}\Z")
```

首字符后要求至少 1 个字符，即**版本号最短 2 字符**。单字符版本（"3"）不匹配，导出阶段即拒。
无 conan 配置可放宽（`core:allow_uppercase_pkg_names` 仅控制大小写，与版本长度无关）；
`conan config list` 无版本长度相关开关。知识库正式条目（E036/E392/E472/E478/E533 等）
均不覆盖该错误面（E478 是"点号版本号 package ID 解析"问题，方向相反）。

## 最小修复方案

将版本号从单数字改为上游完整版本标识（"3" → "3.0"），并保持版本目录、conanfile.py
`version`、分支、delivery_allowed_paths 白名单四处一致：

| 项 | R01（被拒） | R02（通过） |
|----|------------|------------|
| 版本目录 | archives/b/btyacc/3/ | archives/b/btyacc/3.0/ |
| conanfile.py version | "3" | "3.0" |
| 分支 | feat/btyacc-3 | feat/btyacc-3.0 |
| delivery_allowed_paths | archives/b/btyacc/3/** | archives/b/btyacc/3.0/** |

若任务头已固定单数字版本与白名单路径（执行端无权改），把该工具链硬约束作为真实首错
以同一 task_id 回报，由分析端修正任务数据后重新下发（btyacc R01→R02 即此流程）。

## 实际验证结果

- R01：conan-verify G2 FAIL，`conan-create.log` 唯一内容即 `Invalid package version '3'`。
- R02：conan-verify G0-G4/L2/L4/L5 全 PASS，conan create（含 test_package smoke）exit 0。
- 版本号 "3.0" 合法性的最小实证：临时 recipe `version = "3"` → 拒；`version = "3.0"` → 通过。

## 适用范围（何时命中）

- 任务/上游版本号为单数字或单字符（"3"、"9"、"2" 等），conan create 报
  `Invalid package version '<c>'`。
- 仓库内 disktype/9、repo/2 即单数字版本形态，走 conan 配方流程时同样命中此问题。

## 非适用边界（反例）

- 版本号已 ≥2 字符或含点号（"3.0"、"1.9.8"、"20260905"）→ 不适用。
- `Invalid package version` 若源于包名大写/大小写 slug（如 SDL2_image 大写目录），
  属 L0m-5 / E416 双 case slug 问题，不适用本条目。
- 版本号本身合法但 conan create 失败的其他编译错误 → 不适用。

## 限制

- 校验正则随 Conan 版本可能变化；证据基于 Conan 2.29.1（OHOS 适配版，本地与 CI 同源）。
- 未覆盖 Conan 2.30+ 若放宽/收紧后的行为，需按当时基线复核后更新。
