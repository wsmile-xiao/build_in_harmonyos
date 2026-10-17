# 测试报告 — libblocksruntime 0.4.1

> **项目**: BlocksRuntime 0.4.1（C 静态库）
> **测试日期**: 2026-09-15
> **测试环境**: HarmonyOS HongMeng Kernel, aarch64（真机）, OHOS clang 15
> **测试类型**: 上游测试 + 多消费者端到端

---

## 一、测试摘要

| 指标 | 数量 | 百分比 |
|:----:|:----:|:------:|
| 上游测试 | 1 | 1/1（100%） |
| 消费者测试程序 | 3 | 3/3（100%） |
| 消费者断言 | 32 | 32/32（100%） |

**核心功能通过率**: **100%**

---

## 二、测试结果

### 2.1 总体评价

✅ **PASS**

### 2.2 上游测试（1/1）

发行包 `Makefile.am` 的 `check_PROGRAMS = blockrt-test` / `TESTS = blockrt-test`，
源 `test/main.c`：`__block int i` + `Block_copy`，三次调用得 3。
因上游 autotools 在 OHOS 上有 E007/E074 问题（见 notes.md），该测试以同一
源文件（`test_upstream.c` verbatim）作为消费者程序运行：**通过**。

### 2.3 消费者测试（3/3 程序，32 项断言）

| 程序 | 覆盖 | 断言 |
|------|------|:----:|
| `test_upstream.c` | 上游 verbatim 测试 | 1 |
| `test_blocks_c.c` | stack/malloc/global block 类别、`Block_copy`/`Block_release` 生命周期、`__block` byref 共享、块作参数/嵌套/数组/结构体捕获、`Block_copy(NULL)`、`_Block_dump` | 21 |
| `test_blocks_cpp.cpp` | C++ 消费者（不自行传 `-fblocks`，验证运行库传播）、捕获 C++ 对象/拷贝构造、`__block`、块参数/返回块/嵌套 | 10 |

关键断言（示例）：

- `((struct Block_layout *)b)->isa == (void *)_NSConcreteStackBlock`
- `Block_copy(stack_block) -> isa == _NSConcreteMallocBlock && flags & BLOCK_NEEDS_FREE`
- `Block_copy(^{ return ++i; })` 跨作用域存活，计数器 11、12
- `__block` 变量的 byref forwarding 使 `shared = 6` 对已拷贝块可见
- C++ 块堆拷贝触发拷贝构造（`Tracker::copies` 增长）

### 2.4 独立上游语料（mackyle BlocksRuntime/tests，51 文件）

对**已安装的** `libBlocksRuntime.a` 编译运行上游测试集（`-fblocks -include testprefix.h`，
无 `main` 的用例改 `-c`）：

| 类别 | 数量 | 例 |
|------|:---:|------|
| PASS（运行 32 + 编译检查 3） | 35 | byref 家族、`recursive*`、`varargs`、`copyconstructor.C` … |
| 负向编译用例复现（XFAIL-OK） | 7 | `sizeof.c`、`k-and-r.c`、`orbars.c`、`varargs-bad-assign.c` … |
| 跳过（记明技术原因） | 6 | 4× 需 `libdispatch`；2× 需 ObjC-GC（`objectRRGC`、`josh.C`） |
| 上游 legacy 预期偏离 | 3 | `hasdescriptor.c`（尺寸 36 vs 40）、`copy-block-literal-rdar6439600.c`（上游 `CONFIG open`）、`voidarg.c`（源码注明 gcc/clang 均接受 K&R） |
| **OHOS 回归失败** | **0** | — |

### 2.5 编译期/链接期 2×2 矩阵（实测）

| `-fblocks` | 链接运行库 | 结果 |
|:---------:|:---------:|------|
| ✅ | — | 编译过（不代表可用） |
| ❌ | 任意 | `error: blocks support disabled ... -fblocks` |
| ✅ | ❌ | `ld.lld: error: undefined symbol: _NSConcreteStackBlock / _Block_copy` |
| ✅ | ✅ | 编译+链接+运行通过 |

### 2.6 已知限制

1. OHOS clang（harmonybrew 的 23.x）本身没有链接器驱动，直接用它会得到
   `posix_spawn failed` 之类的误导信息；应使用 SDK 的 clang（Conan profile
   `tools.build:compiler_executables` 指向的 `ohos-sdk@.../llvm/bin/clang`），
   链接期缺运行库才会得到真正的 `undefined symbol: _Block_copy`。
2. `runtime.c` 依赖编译器内建原子操作（`__sync_bool_compare_and_swap`），
   非 clang/GCC 工具链不适用。

---

## 三、测试环境

```
OS: HarmonyOS (OHOS) aarch64, HongMeng Kernel 1.12.0
Compiler: OHOS clang（SDK 15 / profile ohos-aarch64）
Package: libblocksruntime/0.4.1（lib/libBlocksRuntime.a + include/Block.h）
Runner: conan create -> ctest（test_upstream, test_blocks_c, test_blocks_cpp）
```

---

*报告生成时间: 2026-09-15*
