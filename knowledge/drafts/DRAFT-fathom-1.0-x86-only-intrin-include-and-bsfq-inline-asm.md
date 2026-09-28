# DRAFT-fathom-1.0: 上游源码中的 x86 专属代码（无守卫的 x86intrin.h 包含 + bsfq 内联汇编）在 aarch64 交叉编译时的补丁模式

## 症状

在 OHOS（aarch64/musl）目标下编译 fathom 1.0 的 `src/tbprobe.c` 时，在到达任何实际编译诊断之前就失败：

```
In file included from src/tbprobe.c:32:
.../x86intrin.h: error: "This header is only for x86"
```

即使绕过头文件问题（例如上游 Makefile 已经传了 `-D TB_NO_HW_POP_COUNT`，
使 `_mm_popcnt_u64` 不会被引用），链接前汇编阶段仍会报错——`lsb()` 里有
无任何条件编译守卫的 x86 内联汇编：

```c
static inline unsigned lsb(uint64_t b)
{
    size_t idx;
    __asm__("bsfq %1, %0": "=r"(idx): "rm"(b));
    return idx;
}
```

aarch64 clang: `error: unknown instruction` / 输出约束不匹配，构建必失败。

## 根因

上游 Makefile 只服务 x86/macOS 作者自己的机器（`CC=clang -std=gnu99`，
`-D TB_NO_THREADS -D TB_NO_HW_POP_COUNT`）。两类 x86 专属构造没有守卫：

1. `#include <x86intrin.h>` 在 tbprobe.c 顶部**无条件**包含。clang 的该头文件
   对非 x86 目标直接 `#error "This header is only for x86"`。它唯一喂进来的是
   `_mm_popcnt_u64`（`popcount` 宏），而那个宏本身已经在
   `#ifndef TB_NO_HW_POP_COUNT` 守卫内、且有纯 C 回退实现——
   **定义了 TB_NO_HW_POP_COUNT 后这个头文件在非 x86 上毫无用处**。
2. `lsb()` 的 `bsfq` 内联汇编无条件编译，完全没有非 x86 分支。
   `TB_NO_HW_POP_COUNT` 宏只解决 `popcount`，解决不了它。

关键判断：**"定义一个宏"和"打平台补丁"是两件事**。预检（grep
`x86intrin|bsfq|__asm__|_mm_`）扫出 x86 intrinsic 时，要同时检查
`__asm__` 内联汇编——宏守卫（TB_NO_HW_POP_COUNT 这类）掩盖了头文件
问题的一半，让人误以为只需编回去就行。

## 方案

用 `conan.tools.files.replace_in_file` 在 `source()` 里加**目标架构守卫**
（不是 `__OHOS__` 守卫——回退分支对所有非 x86 目标都成立，语义更诚实）：

```python
tbprobe_c = os.path.join(self.source_folder, "src", "tbprobe.c")
replace_in_file(self, tbprobe_c,
    "#include <x86intrin.h>",
    "#if defined(__i386__) || defined(__x86_64__)\n"
    "#include <x86intrin.h>\n"
    "#endif")
replace_in_file(self, tbprobe_c,
    '    __asm__("bsfq %1, %0": "=r"(idx): "rm"(b));',
    "#if defined(__i386__) || defined(__x86_64__)\n"
    '    __asm__("bsfq %1, %0": "=r"(idx): "rm"(b));\n'
    "#else\n"
    "    idx = (size_t)__builtin_ctzll(b);\n"
    "#endif")
```

要点：

- `__builtin_ctzll(b)` 对非零输入与 `bsfq` 语义相同。必须核实上游所有
  `lsb()` 调用点保证输入非零（fathom 全部以 `for (; b; b = poplsb(b))`
  形式调用），否则 ctzll(0) 是未定义行为。
- 宏组合用上游 Makefile 原配：`-D TB_NO_THREADS -D TB_NO_HW_POP_COUNT`
  （前者去掉 pthread 依赖，后者走纯 C popcount 回退）。
- 验证：helper API（`tb_lsb`/`tb_pop_count`/`tb_king_attacks`）恰好执行
  被补丁的 `lsb()`/`popcount()` 路径——test_package 不需要 Syzygy 表文件
  就能实质覆盖修复点（避开"编译过=适配完"的假阴性，见 R40/R51）。
- 编译级验证可用 OHOS SDK clang：
  `clang --target=aarch64-linux-ohos --sysroot=<SDK>/sysroot -std=gnu99 ...`。

## 适用范围

任何"上游在 x86 上开发、源码里直接写 x86 intrinsic/内联汇编"的 C/C++ 库
（棋类引擎、模拟器、性能库常见）。先 grep `x86intrin|immintrin|_mm_|bsf|__asm__`
预检；有宏守卫的 intrinsic 用宏解决，裸内联汇编必须加平台分支补丁。
