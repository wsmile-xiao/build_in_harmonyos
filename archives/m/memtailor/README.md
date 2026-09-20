# memtailor — C++ 专用内存分配器库（Arena + 固定尺寸 BufferPool）

## 概述

memtailor（Macaulay2/memtailor）是 Macaulay2 / Frobby 生态里的 C++ 专用内存
分配器库（BSD-3-Clause，"Modified BSD"）。它不追求通用，只做两件在特定场景下
比 `new/delete` 更快、更可预测的事：

- **`memt::Arena`**：栈式（LIFO）分配器。申请便宜、一次释放多个、不越出 C++
  标准、不会爆栈，且同一个进程里可以并存多个互不干扰的 Arena。
- **`memt::BufferPool`**：固定尺寸缓冲池（内部 free list），适合链表节点这类
  同尺寸高频申请。

外加一个从 Arena 取数组内存的 `memt::ArenaVector<T, bool FreeMemory>`。

**本仓库适配版本**：1.4（HarmonyOS PC aarch64）

## 功能概述

- `memt::Arena`
  - `alloc(size)` / `allocObject<T>()` / `allocArrayNoCon<T>(n)`
  - 栈序释放 `freeTop(p)` / `freeAndAllAfter(p)`，整体释放 `freeAllAllocs()`
    / `freeAllAllocsAndBackingMemory()`
  - 自省：`fromArena(p)` / `isEmpty()` / `getMemoryUse()` / `getAllocatedMemoryUse()`
  - 后备块按几何级数增长（`growCapacity()`：新块 = max(所需, 当前块) × 2，
    且不小于 `16*1024 - sizeof(Block) - 16`）
- `memt::BufferPool`
  - `alloc()` / `free(p)` / `fromPool(p)` / `getBufferSize()` / `getMemoryUse()`
  - `freeAllBuffers()` / `freeAllBuffersAndBackingMemory()`（归还后备内存后仍可继续分配）
- `memt::ArenaVector<T, FreeMemory>`：`push_back` / `pop_back` / `clear` /
  `size` / `empty` / `begin` / `end`；`FreeMemory=true` 时析构归还其数组在 Arena
  里占用的那块内存，`false` 时保留（元素析构照常进行）

## OHOS 适配要点

1. **对齐契约就是平台宽度**：`src/memtailor/stdinc.h` 里
   `MemoryAlignment = static_cast<unsigned int>(sizeof(void*))`。
   aarch64/OHOS 上是 **8**，`Arena::alloc()` 与 `BufferPool::alloc()` 都保证返回
   地址整除它。另外 `BufferPool(n)` 的实际缓冲尺寸是
   `align(max(n, sizeof(FreeNode)))`，所以 `BufferPool(1).getBufferSize()`
   在 aarch64 上恰好等于 `sizeof(void*)`。
2. **后备内存来自 `new char[]`**（`MemoryBlocks.cpp`），因此首块地址满足
   `__STDCPP_DEFAULT_NEW_ALIGNMENT__`，position 只按 `MemoryAlignment` 的整数倍
   推进 —— 8 字节对齐这条契约在 aarch64 上恒成立。
3. **memtailor 自身不是线程安全的**（文档明示一个 Arena/BufferPool 只给一个线程
   用）。OHOS 上要验证的是"每线程各持一份时，bionic 的 `std::thread` +
   `operator new/delete` 之下行为逐位可复现"，而不是"共享分配器是安全的"。
4. **测试依赖走 Conan 而非上游的联网通道**：上游 `find_package(GTest)` 失败时
   会退回 `FetchContent` 在 configure 期 git clone googletest v1.16.0，CI worker
   不可联网。本包用 `test_requires("gtest/1.17.0.1")`（ohpcd 已发布：
   OHOS/armv8/clang15/libc++/cppstd17）让 `find_package(GTest)` 直接命中。
5. **ctest 必须在 build 根目录能跑起来**：上游把 `include(CTest)` 写在
   `src/CMakeLists.txt`（子目录）里，`enable_testing()` 只对 `build/src/` 生效，
   在 build 根目录跑 `ctest` 会得到 `No tests were found!!!` 且**退出码为 0**。
   本包把 `include(CTest)` 提到顶层，并在 `build()` 里解析 ctest 汇总行而不只看
   退出码。

## 依赖关系

- 编译依赖：无（只链接 `Threads::Threads`）
- 测试依赖：`gtest/1.17.0.1`（`test_requires`，仅测试期）
- 运行依赖：无

## 打包产物

```
include/memtailor.h
include/memtailor/{Arena,ArenaVector,BufferPool,MemoryBlocks,stdinc}.h
lib/libmemtailor.a
licenses/LICENSE
```

> 上游 `install(TARGETS memtailor LIBRARY DESTINATION lib)` 只声明 `LIBRARY`，
> 静态库（`ARCHIVE` 类别）不会被安装；`memtailor.h` 只挂在 `PUBLIC_HEADER`
> 属性上而没有对应的 `PUBLIC_HEADER DESTINATION`，同样漏装。本包的两个补丁
> 把两者补齐。

## 参考链接

- 上游仓库：https://github.com/Macaulay2/memtailor
- 本仓库版本笔记：`1.4/notes.md`
