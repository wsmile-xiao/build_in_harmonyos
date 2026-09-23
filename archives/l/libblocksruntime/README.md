# libblocksruntime

> clang `-fblocks` 语言扩展所需的 **Blocks 运行库**（LLVM compiler-rt 的
> BlocksRuntime 部分，发行版包名 `libblocksruntime`）。

## 简介

Clang 用 `-fblocks` 支持 C/C++ 的闭包语法 `^{ ... }`，但**语言特性与运行库
是分开的**：编译器把闭包 lowering 成对运行库的调用
（`_Block_copy` / `_Block_release` / `_Block_object_assign` /
`_Block_object_dispose` / `_NSConcreteStackBlock` 等）。若目标平台没有链接
BlocksRuntime，代码可以编译，但在**链接期**失败。

本包提供该运行库：`libBlocksRuntime.a` + `Block.h` / `Block_private.h`。

## OHOS 适配要点

- **症状**：鸿蒙 clang 能编译 `-fblocks` 代码，但 SDK 既不带运行库也不带
  `Block.h`；含块的程序链接时出现上述 `_Block_*` / `_NSConcrete*Block`
  未定义符号。
- **方案**：安装独立 BlocksRuntime，消费者用 `-fblocks` 编译并链接
  `-lBlocksRuntime`。
- 本包通过 `cpp_info.cflags`/`cpp_info.cxxflags` **传播 `-fblocks`**，因此
  消费者只需 `target_link_libraries(app PRIVATE BlocksRuntime::BlocksRuntime)`
  即可同时获得语言开关与运行库。
- 上游 0.4.1 用 autotools 打包，但其 2013 版 `config.guess`/`config.sub`
  不识别 HarmonyOS，且 HMDFS 上 `make` 的 jobserver FIFO 受限；因源码只有
  `runtime.c` + `data.c` 两个翻译单元，本包直接编译（见 `notes.md`）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| （无） | - | 仅 C 标准库 + 编译器内建原子操作（`__sync_bool_compare_and_swap`） |

## 使用

```cmake
find_package(BlocksRuntime REQUIRED)
add_executable(app app.c)
target_link_libraries(app PRIVATE BlocksRuntime::BlocksRuntime)  # 自带 -fblocks
```

```c
#include <Block.h>
typedef int (^IntBlock)(void);
__block int i = 0;
IntBlock b = Block_copy(^{ return ++i; });
b(); b();
Block_release(b);
```

## 参考

- [上游仓库（compiler-rt BlocksRuntime 快照）](https://github.com/mackyle/blocksruntime)
- [LLVM compiler-rt](https://compiler-rt.llvm.org/)
