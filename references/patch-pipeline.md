> 本文件从 SKILL.md v4.8 提取，详细内容供按需加载。

# Phase 3 补丁管线规则与补丁"三可"原则

来源: SKILL.md §2.4, §3.2

---

## Phase 3 补丁管线规则（⚠️ 强制）

**Phase 3 绝对禁止生成 .patch 文件。**

Phase 3 的职责只有两件事：
1. **修改源码**解决编译问题
2. **在 notes.md 记录**每个修改的意图

原因：Phase 3 源码处于频繁试错状态，此时生成的补丁是中间态。
补丁生成**唯一入口**是 Phase 4 的 `ohc-run.py refresh-patch --auto`。

### 允许的操作

- ✅ `sed` / 直接编辑源码（解决编译问题）
- ✅ 创建 post-configure hook 脚本（§3.9）
- ✅ 在 notes.md「源码修改清单」中记录

### 禁止的操作

- ❌ 生成任何 `.patch` 文件
- ❌ 手动写 diff 内容到文件
- ❌ AI 生成补丁文本写入文件
- ❌ copy 之前的 `.patch` 文件

---

## 补丁"三可"原则（§3.2）

所有源码修改必须以 `.patch` 文件保存（由 `ohc-run.py refresh-patch --auto` 生成），满足：

- **可复现**：原始 tarball + 补丁集 → 100% 重现相同产物
- **可验证**：`patch --dry-run -p1` 干净通过
- **可上游**：逻辑清晰、有 `#ifdef __OHOS__` 守卫、可提交给上游

**禁止**：sed 直接改 configure/Makefile 等生成文件（不可复现）。

### 修改层级优先级

```
① configure.ac / CMakeLists.txt / 源码（*.c, *.h）   ← 最优先
② configure / Makefile.in                              ← 次选（生成文件，可从 .ac/.am 重新生成）
③ Makefile                                              ← 最后手段（完全生成文件）
④ 二进制文件                                            ← 绝对禁止修改
```

**原则**：始终优先修改源文件层级（Level ①），这样修改才可复现、可上游。
