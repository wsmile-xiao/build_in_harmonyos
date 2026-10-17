# Draft: C++ 头文件使用 placement new 但未包含 <new>

(配套 DRAFT-micro-gl-3.20-placement-new-missing-new-include.kv)

## 错误特征

消费者以 C++11 编译 `test_microgl.cpp`（仅 include 上游头文件）即失败：

```
include/microgl/bitmaps/buffer.h:46:13: error: no matching 'operator new' function for
  non-allocating placement new expression; include <new>
            new (mem+ix) element_type();
```

报错点在 `buffer<element_type>::allocate_and_construct()`——头文件内直接调用
placement new，但文件顶部没有 `#include <new>`。

## 根因

C++ 的 placement `operator new` 声明位于标准头 `<new>`。上游 `buffer.h` 直接使用
`new (mem+ix) element_type()` 却未包含该头，属头文件自包含（header self-containment）
缺失。OHOS 默认 libc++ 不把 placement 声明随其他标准头隐式带入，编译期即暴露；
在部分 libstdc++ 实现上可能被其他头顺带带入而"偶然可编译"，换标准库实现才暴露。
与链接期 `undefined symbol: operator new`（E247，pkg-config 静态库缺 C++ 运行时）不同：
本条是**编译期**缺标准头声明。

## 修复

源码最小补丁（patches/0002）：在 `buffer.h` 的 `#pragma once` 之后补标准头包含：

```diff
 #pragma once
 
+#include <new>
+
 namespace buffer_traits {
```

验证：`git apply --check` 通过 → `clang++ -std=c++11 -I include -c test_microgl.cpp` 退出码 0。

## 适用边界

- 头文件/内联代码中直接使用 placement new 或显式构造 `new (addr) T` 的 C++ 库；
- 目标标准库为 libc++（OHOS/musl 系、部分嵌入式）时必然暴露；
- 其余实现可能因顺带包含而掩盖，修复不破坏任何实现。

## 反例与限制

- 禁止宏替换或 `#define new` 掩盖——改变语言语义，属 UB；
- 禁止仅消费者侧 `-include <new>` 作为唯一修复——扩散面大，根因在头文件自包含；
- 本条不适用链接期 `undefined symbol: operator new`（那属 E247 静态库 C++ 运行时缺失）。
