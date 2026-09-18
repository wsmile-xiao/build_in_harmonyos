# DRAFT-lzham-1.0-stable1-musl-alloc-alignment — OHOS musl 极小分配仅 8 字节对齐破坏 16 对齐不变量

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-08
> **Severity**: 🟡 medium | **Category**: platform / portability / libc / memory / alignment

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E476**（foonathan/memory 小对象分配未满足 max_align_t 对齐） | 正式收录 | OHOS musl 小尺寸 malloc/operator new 可能仅 8 字节对齐，破坏 foonathan/memory 的 max_alignment(16) 契约；方案为 `posix_memalign(max_alignment, size)` + `std::free` | 同因果（musl 小分配 8 对齐 vs 16 契约），但**覆盖面不同**：E476 仅覆盖 foonathan/memory 的 malloc/new 分配器；本条目覆盖 **(a) 2015 年代自定义分配器封装整层**（如 lzham `lzham_default_realloc`），以及 **(b) musl realloc 移动分配也可能落到 8 对齐小块——realloc 返回值必须同样复检对齐并修复**（E476 未覆盖 realloc 路径） |
| **E133**（musl 头遮蔽） | 正式收录 | -isystem 使 musl libc 头遮蔽编译器内建头 | 非本题——那是 **头文件搜索路径**，本条目是 **分配器返回地址对齐** |

> 全库查证（2026-09-08）：`lzham_realloc: bad ptr` 命中 0 条；`malloc.*8.*align|memalign` 无同库命中；与 E476 属部分覆盖关系，新增差异已实测（realloc 8 对齐触发 + memalign 修复后 8/8 + 全矩阵通过）。

## Scope（何时用）

在 OHOS / HarmonyOS（musl 运行时）上构建或运行**自带对齐契约的自定义分配器**的 C/C++ 库时，若出现：

- 间歇性 `*_realloc: bad ptr` / `*_free: bad ptr` / `Assertion failed: "...bad ptr"` 断言（**Release 下 flaky，同一命令时成功时失败**）；
- 触发点集中在字节矢量/小对象扩容（如符号编码器输出缓冲）；
- 调试构建（ASan/地址消毒器）**稳定通过**——ASan 分配器返回 16 对齐掩盖了缺陷；
- 已实测目标运行时 `malloc(2/3)` 返回仅 8 对齐地址。

典型实例：lzham 1.0-stable1（`lzham_mem.cpp` `lzham_default_realloc`，LZHAM_MIN_ALLOC_ALIGNMENT=16）。

## Symptom

```text
/storage/.../lzham_mem.cpp: Assertion failed: "lzham_realloc: bad ptr"
# 指针实测仅 8 字节对齐（如 0x...9b68 & 0xF == 8），并非随机损坏：
#   同一命令 5 次运行中 ~60-80% 失败（堆布局相关）
# 最小程序实测: malloc(2)=0x...9b68 align=8, malloc(3)=align=8（musl）
#               glibc 对照: malloc(1..16) 恒 align=0
```

## Root Cause

1. musl 运行时对极小尺寸分配（实测 2/3 字节）只保证 8 字节对齐；glibc 对
   `malloc(1..16)` 恒返回 16 对齐，因此 2015 年代代码的"所有分配 16 对齐"
   不变量在 glibc 上成立、在 OHOS musl 上被破坏。
2. 库自定义分配器（`lzham_default_realloc`）直接 `malloc(size)`，未强制对齐；
   矢量首次分配得到 8 对齐指针，后续 `realloc` 输入违反 16 对齐断言。
3. musl `realloc` 移动分配时目标小块同样可能 8 对齐——**单纯修初始分配不够**，
   realloc 返回值必须复检。
4. flaky 根因：是否命中取决于 musl 堆布局，因此 Release 间歇失败；ASan 分配器
   返回 16 对齐导致调试构建绿——不能以 ASan 通过判定无缺陷。

## Fix

`lzham_mem.cpp`（或等价自定义分配器）非 WIN32 路径：

```c
// 初始分配: 保证 16 对齐
p_new = memalign(LZHAM_MIN_ALLOC_ALIGNMENT, size);

// movable realloc 分支: 复检返回值对齐
p_new = realloc(p, size);
if (p_new && ((uintptr_t)p_new & (LZHAM_MIN_ALLOC_ALIGNMENT - 1))) {
    void* p_aligned = memalign(LZHAM_MIN_ALLOC_ALIGNMENT, size);
    if (p_aligned) {
        memcpy(p_aligned, p_new, min(size, malloc_usable_size(p)));
        free(p_new);
        p_new = p_aligned;
    }
}
```

## Verification

- 触发前提实测：最小程序 `for sz in 1..16: malloc(sz)` 打印 `(uintptr_t)p % 16`，
  在 OHOS musl 下 `malloc(2/3)` 出现 8 对齐。
- 修复验证：`conan create ... lzham 1.0-stable1` 通过；`./lzhamtest -v -m4 -d15 c
  <input> <out>` 连跑 8 次全 exit 0；`-m0..-m4` 全级别、字典 `-d15/-d28`、
  递归/解压/`-r`/`-x`/`-e` 等全选项矩阵通过；消费者 test_package 往返 1/1 通过。

## Boundary / 反例

- glibc 或后续修复对齐保证的 musl 版本不触发（malloc 极小尺寸也 16 对齐）。
- 无自定义对齐断言、直接用标准库容器的库不触发。
- **不可**用降低对齐阈值（如把对齐常量改为 8）的方式"修复"——断言是真实
  不变量，掩盖会导致设备上未对齐访问。

## Relation

- similar_to: [E476]（musl 小分配对齐；E476 覆盖 malloc/new 分配器，本文档
  追加 realloc 路径与自定义分配器层）
- caused_by / prerequisite_of / conflicts_with: 无