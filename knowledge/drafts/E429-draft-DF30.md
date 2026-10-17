# E429（DRAFT）：未初始化结构体指针成员在严格分配器上触发 invalid free

> Status: **DRAFT**（路径 B 知识库扩展草稿，待主编 promote）
> Source: ylva 1.7 适配（PR #14061 / CI 构建 #65823）
> 对应: `knowledge/drafts/E429-draft-DF30.kv` · 提议编号 E429（仓内 `graph validate` 报告的编号空洞）

---

## 相关既有条目

先撞库再立项。检索方式与结果：

```bash
python3 scripts/ohc-run.py engine "invalid free SIGTRAP rc=-5 free(): invalid pointer musl malloc uninitialised struct"
grep -Ei 'invalid free|SIGTRAP|invalid pointer|uninitial|MallocScribble|MALLOC_PERTURB|free\(\)' knowledge/graph/index.tsv
grep -RliE 'invalid free|SIGTRAP|invalid pointer|uninitialis|uninitializ|MallocScribble|MALLOC_PERTURB' knowledge/doc/
```

`index.tsv` 对上述关键词**零命中**；`doc/` 命中 3 条，逐条判定如下：

| 条目 | 已覆盖内容 | 本条目增量 |
|---|---|---|
| **E249**（未初始化所有权标志导致清理函数释放调用者栈对象） | 构造子对象时未初始化 **shared/owned 所有权标志**，清理函数读该标志后按独占语义 `free` 调用者的**栈对象**；症状 `Signal 11 (core dumped)` / ASan `attempting free on address which was not malloc()-ed`；回退方案正是"整体零初始化结构体" | 本草稿的失效面是**结构体自身的指针成员**（不是所有权标志），被释放的是**本进程 malloc 出来的野指针**（不是调用者栈对象），触发路径是**查询未命中→回调未执行→无条件清理**；真正的增量是**只现形于严格分配器**这一点：同一份代码在 glibc/macOS 上零页侥幸通过、在 OHOS 上必崩，并给出在本机把这类 UB 变必现的三种手段。E249 无法直接复用，因为它的判据假设"清理函数按标志决定是否释放"，而这里的清理函数是**无条件**逐字段 `free` —— 有标志也救不了未初始化的字段本身 |
| E292（大型 C++ 数据处理库上游测试在 OHOS 上需要分层迁移和环境补齐） | 把 `SIGTRAP` 作为长错误签名中的一项列出（伴随大量测试环境问题），属于"上游测试套件整体迁移"的集合条目 | 本草稿是单机制条目：解释 `SIGTRAP` 从何而来（非法 `free` 就地终止）、如何在本机预判、如何最小修复；与"测试套件迁移"无重叠 |
| E224（线程 alternate signal stack 生命周期） | `engine` 因 "free + memory + runtime" 关键词命中的**最相近条目**，讲的是 `sigaltstack` 注册资源与 backing memory 的回收顺序 | 机制完全不同（信号栈生命周期 vs 未初始化字段），仅共享"内存回收顺序"抽象；不构成覆盖 |

结论：**部分相关，可独立新建**；`.kv` 已把 `similar_to` 填为 `[E249]`。

## Scope

适用于所有满足以下形状的 C/C++ 代码：

1. 存在"只分配不初始化"的工厂函数（`x_new_empty()` / `malloc(sizeof(struct))` 后直接返回）；
2. 该结构体带有**需要被清理的指针成员**（字符串、链表 next、缓存 buffer…）；
3. 清理函数对指针成员**无条件** `free`，且在"查询/解析未命中"这类失败分支上仍会被调用。

典型现场：本机（glibc 或 macOS）测试全过，一进 OHOS CI 就出现目标用例 `rc=-5`，且崩溃点与业务逻辑无关（删掉该用例后其它用例全过）。

不适用于：结构体分配后立即被完整初始化、或清理函数本来就在所有分支判空的情况。

## Symptom

真实 CI 日志（PR #14061 / 构建 #65823，`test_package` 阶段）：

```text
o  [PASS] F8 list-all on an empty database  -- rc=0
o  [FAIL] F9 list-entry on a missing id  -- rc=-5
...
oRESULT: passed=24 failed=1
```

`rc=-5` 即被 signal 5 终止，与 `ylva -l <缺失 id>` 走的是"查询未命中→清理"这条平时没人走的路径吻合。

本机把同一份**未打补丁**源码跑成必现（macOS arm64）：

```text
$ MallocScribble=1 ./ylva -l 99
Nothing found with id 99.
rc=134                      # 未打补丁：invalid free

$ ASAN_OPTIONS=detect_leaks=0 ./ylva-asan -l 99
==54705==ERROR: AddressSanitizer: SEGV on unknown address 0xffffbebebebebeae
    #0 ... in __asan::Allocator::Deallocate
    #1 ... in free
    #2 ... in entry_free+0x60
    #3 ... in main+0x3e8
rc=141
```

ASan 栈直接落在 `free ← entry_free ← main`，与被释放指针是未初始化的 `0xbebe…` 填充值一起，把"野指针 free"钉死。

## Root Cause

机制链（ylva 实例）：

```text
db_get_entry_by_id(id)
  → entry_new_empty()            /* malloc(sizeof(Entry_t))，7 个字段全不初始化 */
  → sqlite3_exec("select ... where id=N")
  → 没有匹配行 ⇒ 回调 cb_get_by_id() 根本不执行
list_by_id(id)
  → entry->id == -1（唯一被赋过值的字段）
  → entry_free(entry)
      → free(entry->title/user/url/password/notes)   /* 全部是垃圾指针 */
```

为什么"平台差异"只是表象：

- **glibc / macOS**：`malloc` 在小对象刚由整页映射而来时返回**全零**内存，指针成员恰为 `NULL`，`free(NULL)` 按 POSIX 是空操作 ⇒ **静默通过**。
- **OHOS（musl）**：分配器复用的是**脏内存**，指针成员是垃圾值，释放非法地址时分配器不静默容忍，而是**就地终止进程**（实测 signal 5 / 退出码 -5）。

因此根因是**平台无关的上游内存安全缺陷**；平台差异只决定它"是否现形"。这也解释了为什么这类问题几乎总是"本机全绿、OHOS 必崩"。

## Recommended Fix / Workaround

在"只分配不初始化"的工厂函数里，`malloc` 之后立即整体清零：

```c
Entry_t* entry_new_empty()
{
    Entry_t* new = NULL;
    new = tmalloc(sizeof(struct _entry));
    memset(new, 0, sizeof(struct _entry));   /* ← 新增：指针成员先成为 NULL */
    return new;
}
```

- 失败路径：清理函数看到的是 `NULL`，`free(NULL)` 是空操作；`entry->stamp` 判空分支也自然成立。
- 成功路径：sqlite 回调随后给每个字段赋值，行为与修改前完全一致。
- 纯 C 标准库调用、**不含平台宏** ⇒ 对非鸿蒙平台透明，可直接向上游提交（符合 R8/PF5）。

仓内落补丁方式（R3：补丁只由工具生成）：

```bash
python3 scripts/ohc-run.py track-edit add ylva 1.7 src/entry.c   # 或用 .orig/.work 目录对比
python3 scripts/ohc-run.py refresh-patch --auto ylva 1.7
```

## Fallback

若构造方不方便改（例如结构体由第三方库分配、或接口已冻结），退到清理函数里逐字段判空：

```c
if (entry->title)    free(entry->title);
if (entry->user)     free(entry->user);
...
if (entry->stamp)    free(entry->stamp);
```

注意：必须**每个**指针字段都守护，漏一个（例如只补了 `title` 而忘了 `next`）仍旧会崩，因此这是回退方案而非首选。

## Forbidden Approaches

| 禁止写法 | 为什么 | 后果 |
|---|---|---|
| 跳过 / 删除触发用例（`跳过该用例`、`移除 test_package`、`rc=-5.*忽略`） | 崩溃是真实缺陷，不是平台差异 | 包"构建通过"但同类路径仍 invalid free，且把可复用的通用问题一起埋掉 |
| 关闭分配器检查（`-Wno-*free`、`MALLOC_CHECK_=0`、`MALLOC_PERTURB_=0`） | 等于拆掉安全网，把可诊断的信号变成静默内存破坏 | 下一次同类 UB 直接退化为随机内存损坏，排障成本成倍上升 |

## Verification

修复前后都可复算（同一条命令即可）：

```bash
# 本机把 UB 变必现（未打补丁应非零终止，打补丁后 rc=0）
MallocScribble=1      ./ylva -l 99        # macOS
MALLOC_PERTURB_=170   ./ylva -l 99        # glibc
ASAN_OPTIONS=detect_leaks=0 ./ylva-asan -l 99   # 栈应指向 free ← 清理函数

# 仓内正式验证
python3 scripts/ohc-run.py conan-verify ylva 1.7 --profile <profile>
```

ylva 实测对照：

| 构建 | 命令 | 结果 |
|---|---|---|
| 未打补丁 | `MallocScribble=1 ./ylva -l 99` | `rc=134`（invalid free） |
| 未打补丁 | 普通 `./ylva -l 99` | `rc=0`（**侥幸通过**——正是 CI 之前本机全绿的原因） |
| 未打补丁 + ASan | `./ylva-asan -l 99` | SEGV，栈 `free ← entry_free ← main` |
| 已打补丁 | 上述三条 | 全部 `rc=0` |
| 已打补丁 | OHOS CI 目标用例 F9 | 退出码不再是 -5 |

## Prevention

1. **工厂函数一律零初始化**：`malloc` 之后紧跟 `memset(...,0,...)`（或 `calloc`），把"未初始化字段"这类 UB 从结构上消灭。
2. **本机预跑严格分配器**：在提 CI 前用 `MallocScribble=1` / `MALLOC_PERTURB_=<非0>` / `-fsanitize=address` 跑一遍 test_package 能覆盖到的路径——**这一步能在提交前把"只现形于 OHOS"的 UB 变成必现**。
3. **失败分支也要覆盖测试**：`查询未命中`/`空结果`/`记录不存在` 这类分支最容易暴露未初始化清理路径，应在 test_package 里显式断言。

## References

- 上游：`nrosvall/ylva` v1.7，`src/entry.c:entry_new_empty()` / `entry_free()`、`src/db.c:db_get_entry_by_id()`
- 本次 PR：OpenHarmonyPCDeveloper/build_in_harmonyos PR #14061（构建 #65823，F9 `rc=-5`）
- 相关条目：E249（未初始化所有权标志 → 释放调用者栈对象）
- 本机复现产物：`MallocScribble=1`（macOS）、`MALLOC_PERTURB_=170`（glibc）、`-fsanitize=address`
