# linenoise-ng v1.0.0：linenoiseHistorySetMaxLen 收缩历史时按容量偏移 memcpy 导致 NULL 解引用崩溃

- **草稿 ID**: DRAFT-linenoise-ng-1.0.0-history-setmaxlen-shrink-null-deref
- **来源**: linenoise-ng v1.0.0 HarmonyOS PC 适配（R01，patch `0002-src-linenoise.cpp.patch`）
- **分类**: upstream-bug / memory / history-buffer / static-lib / regression
- **状态**: 本地草稿（路径 B 知识库扩展，.kv/.md 同 stem 配对）

## 问题 / 错误签名

- **现象**：鸿蒙专项测试 `ohos_test.c`（仅用公开头 `include/linenoise.h`）在
  `linenoiseHistorySetMaxLen(2)` 收缩后调用 `linenoiseHistorySave()` 时进程崩溃
  `Signal 11 (core dumped)`，exit 139。
- **复现命令**（R02 起随 PR 交付，可复现）：
  ```bash
  # ① 鸿蒙专项 15 断言套件（archives/l/linenoise-ng/v1.0.0/test_package/ohos_test.c）
  clang++ -std=c++11 -I<包 include 目录> ohos_test.c <liblinenoise.a> -o ohos_test && ./ohos_test
  # ② 消费者收缩回归（test_package/test.c，conan create 自动运行 ctest）
  clang++ -std=c++11 -I<包 include> test.c <liblinenoise.a> -o t && ./t
  ```
- **触发路径**：默认 `historyMaxLen=100` → 添加少量条目（历史未满）→
  `linenoiseHistorySetMaxLen(2)`（收缩）→ `linenoiseHistorySave()` → SIGSEGV。

## 根因

linenoise-ng v1.0.0 的 `linenoiseHistorySetMaxLen(len)` 在收缩（`len < historyLen`）时：

```cpp
memcpy(newHistory, history + historyMaxLen - tocopy, sizeof(char8_t*) * tocopy);
```

源偏移使用**容量** `historyMaxLen`。当历史未满（`historyLen < historyMaxLen`）时，
`history + historyMaxLen - tocopy` 指向 `malloc+memset` 初始化的**空槽**（NULL），
拷贝进新数组后 `historyLen` 仍 >0 而槽位为 NULL；随后
`linenoiseHistorySave()` 中 `if (history[j][0] != '\0')` 直接解引用 NULL → SIGSEGV。

上游 antirez/linenoise 原版使用 `history + historyLen - tocopy`（只取已填条目尾部），
linenoise-ng 引入此回归。已核对 v1.0.0 源码确认（`src/linenoise.cpp:3082`）。

## 最小修复方案

在 `archives/l/linenoise-ng/v1.0.0/**` 范围内：

1. **源码补丁** `patches/0002-src-linenoise.cpp.patch`：将 memcpy 源偏移改为按已填数
   `historyLen`（恢复 antirez 原版语义）：
   ```cpp
   memcpy(newHistory, history + historyLen - tocopy, sizeof(char8_t*) * tocopy);
   ```
2. **回归测试**（随本 PR 交付，R02 起可复现）：
   - `test_package/ohos_test.c`（鸿蒙专项，非交互）：覆盖 history add/去重/空行/
     换行折叠/`SetMaxLen(0)` 拒绝/收缩到 2 后 Save 只写非空行/Save-Load round-trip，
     15 断言全过（exit 0）；
   - `test_package/test.c`（消费者，conan create L1 自动运行）：追加未满收缩到 2 →
     Save（断言仅非空行）→ Load 回读回归断言，与 ohos_test.c 独立计数。
3. **配方配套**：静态库为 C API + C++ 实现，纯 C 消费者需
   `self.cpp_info.system_libs = ["c++"]`（E247 既有知识）。

## 验证

```bash
# 修复后（随 PR 交付的归档 test_package/ohos_test.c，R02 实测）
clang++ -std=c++11 -I<包 include 目录> test_package/ohos_test.c <liblinenoise.a> -o ohos_test && ./ohos_test
# RESULT: 15/15 checks passed, exit 0
# 消费者收缩回归 test_package/test.c 同样 exit 0
conan create ...                      # G2 干净构建 PASS；W3 本地 CI 1/1 PASS
```

修复前 exit 139（Signal 11），修复后 exit 0——同一测试同一路径复现→修复→回归；
R02 反向核验：仅应用 0001、不应用 0002 重建 lib 后，test.c 第 4 条断言后
Signal 11（exit 139），证明回归断言真实覆盖 0002 修复分支。

## 适用边界

- **触发条件**：任何"历史未满时收缩 maxlen 后访问历史"的消费者，平台无关
  （OHOS 非交互测试只是让该路径可复现）。
- **不适用**：历史恰好满员（`historyLen == historyMaxLen`）时新旧偏移结果相同，
  不触发；`SetMaxLen(0)` 恒返回 0 不生效。
- **跨库复用**：同为"缓冲区/数组按容量而非实际填充数取偏移"的记忆管理模式，
  可推广到同类 history/buffer 收缩逻辑审查；对 linenoise-ng 消费者可直接套用补丁。

## 查重差异（七轴）

| 轴 | 结果 | 说明 |
|----|------|------|
| exact_duplicate | 否 | 图谱无 linenoise/HistorySetMaxLen 条目 |
| causal_duplicate | 否 | E338（/etc/passwd 缺失）、E040（man-db MAN_OWNER）仅症状同为 SIGSEGV，根因完全不同（平台用户表 vs 上游 memcpy 偏移回归） |
| trigger_overlap | 部分 | 与 E338/E040 共享 SIGSEGV/Signal 11 症状关键词（engine 因此命中 E338 Phase B），触发工具链不同 |
| solution_overlap | 无 | E338/E040 为运行时/平台适配方案；本条目为上游源码回归修复 + 回归测试 |
| combination_novelty | 有 | 非交互 OHOS 专项测试暴露上游通用内存 bug → 源码级修复 + 断言回归，构成新组合 |
| boundary_novelty | 有 | 明确"未满时收缩"边界（满员时不触发），既有条目未覆盖该边界语义 |
| test_migration_novelty | 有 | ohos_test.c 把交互式 VT100 库的 history API 转成可 headless 运行的断言套件 |

**关系字段**：`similar_to: E338`（仅症状）、`caused_by: 上游 linenoise-ng v1.0.0 实现回归`、
`prerequisite_of: 无`、`conflicts_with: 无`。

**决定**：`new_draft` —— 候选已验证、可跨库复用、查重未命中，路径 B 成立；
`.md/.kv` 同 stem 配对通过。
