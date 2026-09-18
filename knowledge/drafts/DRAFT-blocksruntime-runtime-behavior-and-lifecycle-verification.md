# DRAFT-blocksruntime-runtime-behavior-and-lifecycle-verification — 移植 BlocksRuntime 后怎么验、断言什么

> 配套第一稿：`DRAFT-ohos-clang-fblocks-missing-blocks-runtime`（为什么需要独立运行库、
> 以及 `-fblocks` 与运行库两半）。本稿解决**移植/打包之后如何验证行为**，以及**上游语料怎么归类**。

## 现象

直接照抄 Apple / 新版运行库语义写断言，会在 compiler-rt **0.4.1** 上产生一批**假失败**：

```
FAIL test_blocks_c.c:61: ((struct Block_layout *)b2)->isa == (void *)_NSConcreteMallocBlock
FAIL test_blocks_c.c:98: ((struct Block_layout *)arr[i])->flags & BLOCK_NEEDS_FREE
Block compiled by obsolete compiler, please recompile source for this Block   (进程 exit 1)
```

以及跑上游语料时出现 `not the same size, using old compiler??` 之类提示。

## 根因（0.4.1 真机实测，OHOS aarch64 / SDK clang 15）

用行为探针打印关键字段，实测矩阵：

| 对象 | isa | flags | NEEDS_FREE | REFCOUNT | HAS_COPY_DISPOSE | descriptor->size |
|------|-----|-------|:---------:|:--------:|:---------------:|:---------------:|
| 栈块（捕获 int） | Stack | `0x40000000` | 0 | 0 | 0 | 36 |
| 无捕获块 | **Global** | `0x50000000` | 0 | 0 | 0 | 32 |
| `__block` 块 | Stack | `0x42000000` | 0 | 0 | **1** | 40 |
| `Block_copy(栈块)` | **Stack**（未变） | `0x41000001` | **1** | **1** | 0 | 36 |
| 再次 `Block_copy` | Stack | `0x41000002` | 1 | **2**（同指针）| 0 | 36 |

关键结论（与 Apple/新版习惯相反）：

1. **0.4.1 的 `_Block_copy` 不重标 `isa`**：堆拷贝的 `isa` 仍是 `_NSConcreteStackBlock`，
   只置 `BLOCK_NEEDS_FREE | 1`（`runtime.c:202-212`）。判“是堆块”要 `NEEDS_FREE=1 且 refcount=1`，
   并确认指针与栈块不同 —— **不能**断言 `isa == _NSConcreteMallocBlock`（实测恒为 0）。
2. **无捕获块是 global block**（`BLOCK_IS_GLOBAL`）：`Block_copy` **原样返回**，不置 `NEEDS_FREE`。
   把“数组里 `Block_copy` 过的块都有 NEEDS_FREE”当契约会假失败。
3. **现代 clang 不置 legacy `BLOCK_HAS_DESCRIPTOR`(0x20000000)**，改置新位 `0x40000000`。
   而 0.4.1 的 `_Block_dump()` 看到 legacy 位缺失就 `printf` + `exit(1)`（`runtime.c:462-465`），
   实测 `dump_rc=1`。**诊断/日志路径不要调用 `_Block_dump`**。
4. 上游 `hasdescriptor.c` 假设 inner/outer `descriptor->size` 相同；实测 **36 vs 40**
   （inner 捕获 4 字节 `int`，outer 捕获 8 字节块指针），属**legacy 预期**，不是移植缺陷
   （本包 `Block_size()` 就是 `descriptor->size` 的直读，`runtime.c:347-349`）。

## 使用说明 / 适用范围 / 输入输出 / 示例

### 使用说明（三步）

1. **跑行为探针**（见「示例」），对照「期望输出」确认运行库的关键契约；
2. **跑上游语料并分类**（PASS / 负向编译复现 / 跳过并记明原因 / 上游 legacy 预期 /
   OHOS 回归），只有最后一类是移植缺陷；
3. **回归到可移植判据**：把测试里依赖具体 `isa`/legacy 位的断言改成
   `BLOCK_NEEDS_FREE`+refcount/global 短路等可移植契约。

### 适用范围

- **适用**：任何 BlocksRuntime 移植/打包（compiler-rt、mackyle、发行版变体）后的行为验证，
  以及含块库的消费者测试设计。
- **不适用**：ObjC ARC/GC 运行时语义、libdispatch/GCD 集成（语料中这类用例按技术原因跳过）。

### 输入 / 输出

| | 内容 |
|---|---|
| **输入** | ① 已安装的 BlocksRuntime（`lib/libBlocksRuntime.a` + `Block.h`/`Block_private.h`）或含块库；② 上游语料（如 mackyle `BlocksRuntime/tests/`，51 文件）；③ 编译器（`-fblocks`）|
| **输出** | ① 行为矩阵表（栈/global/byref/堆拷贝的 `isa`/`flags`/`NEEDS_FREE`/`REFCOUNT`/`HAS_COPY_DISPOSE`）；② 语料分类表（PASS / XFAIL / SKIP+原因 / 上游 legacy 偏离 / OHOS 回归）；③ 可移植断言清单（哪些断言可写、哪些会在 0.4.1 误报）|

### 示例

```sh
# 行为探针（源码见下「可复用验证方法 (a)」）
clang -fblocks -I<pkg>/include probe.c <pkg>/lib/libBlocksRuntime.a -o probe && ./probe
```

期望输出（0.4.1 真机实测）：

```
stack NEEDS_FREE=0
copy sameptr=0 NEEDS_FREE=1 REFCOUNT=1 isa_retag=0
byref HAS_COPY_DISPOSE=1
global copy sameptr=1
```

```sh
# 上游语料（mackyle BlocksRuntime/tests）
clang -w -fblocks -include testprefix.h -I<master> -I<master>/BlocksRuntime \
      -o t <test>.c <pkg>/lib/libBlocksRuntime.a && ./t
# 期望汇总：PASS=32 PASS(compile-only)=3 XFAIL-OK=7 SKIP=6 COMPILE_ERR=0 RUNFAIL=0
```

## 可复用验证方法

### (a) 行为探针（可移植判据，不含 isa 重标/legacy 位）

```c
#include <stdio.h>
#include <Block.h>
#include <Block_private.h>
int main(void) {
    int a = 1;
    void (^s)(void) = ^{ (void)a; };      /* 捕获局部 -> 栈块 */
    void (^g)(void) = ^{ (void)0; };      /* 无捕获 -> global 块 */
    __block int bc = 7;
    void (^by)(void) = ^{ bc++; };        /* __block -> byref，应有 copy/dispose */
    struct Block_layout *ls = (struct Block_layout *)s;
    printf("stack NEEDS_FREE=%d\n", !!(ls->flags & BLOCK_NEEDS_FREE));
    void *h = Block_copy(s);
    struct Block_layout *lh = (struct Block_layout *)h;
    printf("copy sameptr=%d NEEDS_FREE=%d REFCOUNT=%u isa_retag=%d\n",
           h == (void *)s, !!(lh->flags & BLOCK_NEEDS_FREE),
           lh->flags & BLOCK_REFCOUNT_MASK, lh->isa == (void *)_NSConcreteMallocBlock);
    printf("byref HAS_COPY_DISPOSE=%d\n",
           !!(((struct Block_layout *)by)->flags & BLOCK_HAS_COPY_DISPOSE));
    printf("global copy sameptr=%d\n", Block_copy(g) == (void *)g);
    return 0;
}
```

```sh
clang -fblocks -I<pkg>/include probe.c <pkg>/lib/libBlocksRuntime.a -o probe && ./probe
# 0.4.1 期望：stack NEEDS_FREE=0 | copy sameptr=0 NEEDS_FREE=1 REFCOUNT=1 isa_retag=0 |
#            byref HAS_COPY_DISPOSE=1 | global copy sameptr=1
```

即：**断言可移植契约**（拷贝产生新指针、NEEDS_FREE/refcount 语义、global 短路、
byref 生成 copy/dispose 助手），**不要断言具体运行库的 isa 标记与 legacy 位**。

### (b) 上游语料三步法（R51 清点 → 运行 → 归类回填）

对 mackyle/blocksruntime 的 `BlocksRuntime/tests/`（51 文件，独立上游代码库）：

- 编译：`clang -w -fblocks -include testprefix.h -I<master> -I<master>/BlocksRuntime`，
  无 `int main` 的用例改 `-c`；C++ 用例走 `clang++`。
- 归类（**关键**，否则会把 benign 差异当移植缺陷）：

| 类别 | 本任务实测 | 例 |
|------|:---:|------|
| PASS（运行/编译检查） | 35 | `byref*`、`recursive*`、`varargs`、`copyconstructor.C` … |
| 负向编译用例复现 | 7 | `sizeof.c`、`k-and-r.c`、`orbars.c`、`varargs-bad-assign.c` … |
| 跳过（技术原因） | 6 | 4× 需 `libdispatch`；2× 需 ObjC-GC（`objectRRGC`、`josh.C`） |
| 上游 legacy 预期偏离 | 3 | `hasdescriptor.c`（同尺寸假设）、`copy-block-literal-rdar6439600.c`（上游 `CONFIG open`）、`voidarg.c`（源码内注明 gcc/clang 都接受 K&R） |
| **OHOS 回归失败** | **0** | — |

## 禁止做法（实测依据）

- ❌ 断言 `Block_copy` 后 `isa == _NSConcreteMallocBlock`：0.4.1 不重标，实测假 FAIL。
- ❌ 断言“`Block_copy` 过的块都有 `NEEDS_FREE`”：无捕获块是 global 块，`Block_copy` 原样返回。
- ❌ 在诊断/生产路径调用 `_Block_dump`：现代 clang 下它 `exit(1)`（实测 `dump_rc=1`）。
- ❌ 不分类就把上游语料失败记成 OHOS 缺陷：会把 legacy 预期/缺 libdispatch 的用例算进失败率（R51 要求逐项技术原因）。

## 验证

```sh
# 行为探针（上节）与语料脚本均已在本任务真机执行：
#   语料：PASS 32 + PASS(compile-only) 3 + XFAIL-OK 7 + SKIP 6 + COMPILE_ERR 0 + RUNFAIL 0
#   探针：stack NEEDS_FREE=0；copy sameptr=0 NEEDS_FREE=1 REFCOUNT=1 isa_retag=0；
#         global copy sameptr=1；legacy_HAS_DESCRIPTOR=0；clang 新位 0x40000000=1；dump_rc=1
```

## 关联条目

- 配套: `DRAFT-ohos-clang-fblocks-missing-blocks-runtime`（为何需要独立运行库、`-fblocks` 传播）。
- 相似: E019（运行期动态库加载）、E213（缺失接口本地实现）——本稿不涉及链接/部署，而是**运行库行为契约的验证方法**。

## 元信息

- authors: `frj__`（contributor_id: `frj__`）
- source_event: libblocksruntime 0.4.1 行为矩阵 + mackyle 上游语料 51 文件分类（2026-09-15）
- draft: true —— 待主编审核后 promote 为正式 E 条目
