# OHOS PC /storage 大小写不敏感：package() 大小写别名副本 copy2 抛 SameFileError，容错 + 计数 19/14 双值断言

- **草稿 ID**: DRAFT-inform6-compiler-6.42-case-insensitive-alias-samefile
- **来源**: inform6-compiler 6.42 HarmonyOS PC 适配（真机 conan 2.29.1 首验：package() 别名副本循环抛 `shutil.SameFileError`，消费者测试 [1/6] 计数断言失败）
- **分类**: conan / recipe / packaging / filesystem / ohos
- **状态**: 本地草稿（已挂 PR #12688，路径 B 知识库扩展申请中，位于 knowledge/drafts/）

## 问题 / 错误签名

- **SameFileError**：package() 生成大小写别名副本（English.h→english.h 等 5 个，上游 fixlinks.sh 别名软链的 R5 合规替代）时，`shutil.copy2` 抛 `shutil.SameFileError: '.../std/lib/english.h' and '.../std/lib/English.h' are the same file`，打包中断。
- **计数塌缩**：即使跳过异常，目录项在大小写不敏感 FS 上塌缩——`find -type f` 计数从 19（14 上游 + 5 别名副本）变为 14，消费者测试 [1/6] 精确计数断言必挂（`std/lib 文件数 14 != 19`）。
- **可观测特征**：conan create 在 package() 阶段失败退出；或测试输出 `std/lib 文件数 N != 19`。
- **复现**：HarmonyOS PC 真机（aarch64，/storage 大小写不敏感）直接复现；CI Linux 大小写敏感不触发——**仅真机可见**。

## 根因

1. **OHOS PC 真机用户存储 `/storage/Users/currentUser` 是大小写不敏感文件系统**（探针实证：`touch CaseProbe.x` 后 `ls caseprobe.X` 命中同一文件）。
2. **上游 fixlinks.sh 建 English.h→english.h 等 5 个大小写别名软链**；R5 禁止 `ln -sf`，适配改为文件副本。大小写不敏感 FS 上目标别名与源原名解析到同一文件，`shutil.copy2` 抛 SameFileError。
3. **目录项塌缩使 `find -type f` 计数少 5**；测试脚本精确计数断言必挂。CI Linux 大小写敏感：既无异常、计数 19——两处问题对 CI 完全不可见。

## 最小修复方案

conanfile `package()` 别名循环 + `test_inform6.sh` 计数断言：

```python
# 大小写敏感系统（CI Linux）仍产出文件副本；大小写不敏感系统（真机 /storage）别名与原名同文件、无需副本
for src, alias in ALIASES:
    try:
        shutil.copy2(os.path.join(dst_dir, src), os.path.join(dst_dir, alias))
    except shutil.SameFileError:
        pass  # 大小写不敏感文件系统：别名即原文件
```

```sh
# 19=大小写敏感全量（14 上游 + 5 别名副本）；14=大小写不敏感塌缩
NLIB=$(find "$LIB" -type f | wc -l)
[ "$NLIB" -eq 19 ] || [ "$NLIB" -eq 14 ] || fail "std/lib 文件数 $NLIB != 14/19"
```

要点：

- 别名在位检查 `[ -f "$LIB/English.h" ]` 在两种 FS 上均通过，无需改动。
- 真机复验：conan create 6 组断言全过、EXIT=0；CI Linux 计数 19、全量副本在位。

回退方案（copy2 异常语义不可用时）：先用大小写探针（`touch CaseProbe.x && ls caseprobe.X`）判定 FS 敏感性，敏感则跳过别名副本、并保留双值断言——与 try/except 等效。

## 验证结果

| 环境 | 结果 |
|------|------|
| 本地（Windows MinGW）· 按 package() 布局 1:1 模拟包 | 修复前复现计数偏差；修复后 6 组断言全过 |
| HarmonyOS PC aarch64 真机 · Conan 2.29.1 | 修复前 package() SameFileError；修复后 conan create 6 组断言全过、EXIT=0、Package 6b129b06…9ce8a created |
| CI Linux（大小写敏感） | 计数 19、全量副本在位、测试全绿 |

## 禁止策略

- 禁止直接删除别名副本或将其剔出包外——别名是上游 fixlinks.sh 的功能承诺（大小写敏感系统上 `Include "Parser"` 等大写 include 靠它工作），剔除即功能不等价。
- 禁止用 `ln -sf` 软链实现别名——违反 R5，门禁拦截。
- 禁止只加 `except SameFileError` 容错不改计数断言（仍 19 单值）——大小写不敏感 FS 计数塌缩为 14，单值断言必挂；容错与双值断言必须成对落地。
- 禁止"发现异常后删测试断言"——计数断言正是抓目录项塌缩的手段，不应弱化。

## 相关

- 相似条目：E193（大小写敏感测试在 HMDFS 挂——测试用例选择视角）、E416（大小写目录双 case 并存——slug 门禁视角）、E470（BUILD 与 build 目录冲突——构建产物目录视角）；本条为 package() 别名副本 SameFileError + 计数断言视角，与其互补不重叠。
- 关联经验：inform6 6.44-r7 同款修复（计数 15/20 双值断言），说明该模式在同一上游发行线多个包上反复出现，通用性已实证。
