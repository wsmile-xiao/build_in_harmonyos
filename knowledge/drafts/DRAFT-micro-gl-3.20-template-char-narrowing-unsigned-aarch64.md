# Draft: micro-gl C++ 模板非类型参数 char 默认 -1 在 char 无符号目标编译失败

(配套 DRAFT-micro-gl-3.20-template-char-narrowing-unsigned-aarch64.kv)

## 错误特征

消费者以 C++11 编译 `test_microgl.cpp`（仅 include 上游头文件、未写任何模板实参）即失败：

```
include/microgl/math/Q.h:31:38: error: non-type template argument evaluates to -1,
  which cannot be narrowed to type 'char' [-Wc++11-narrowing]
        char multiplication_strategy=-1>
```

`-std=c++14/c++17` 下同样报错（对模板非类型实参该诊断恒为 error）。上游自身
`cmake_minimum_required(VERSION 3.20)` 与 `project(VERSION 1.0.0)` 无法在消费者侧规避。

## 根因

AArch64 ELF ABI 默认 plain `char` 为**无符号**（`CHAR_MIN=0`），x86-64 相反。头文件
`include/microgl/math/Q.h` 以：

```cpp
template <unsigned P, typename integer=int, typename inter_integer=long long,
          char multiplication_strategy=-1>
class Q { ... };
```

声明模板非类型参数：默认实参 `-1` → unsigned char 属窄化转换，clang 直接拒绝实例化。
这是**编译期**问题，与 E419（C 语言运行期 INT8 结果差 256）不同根因、不同阶段：
E419 是「字节不变、整型提升改变比较结果」，本条是「模板实参窄化、编译期硬错误」。

## 修复

源码最小补丁（patches/0001）：

```diff
-        char multiplication_strategy=-1>
+        signed char multiplication_strategy=-1>
```

`-1/0/1/2` 均在 signed char 值域内，下游 `multiplication_strategy==-1` 推理恢复成立。
验证：`git apply --check` 通过 → `clang++ -std=c++11 -I include -c test_microgl.cpp` 退出码 0。

## 适用边界

- 仅影响以 plain `char` 作为模板非类型参数且带负值默认实参的 C++ 头文件库；
- 目标必须是 plain char 无符号平台（OHOS/aarch64、ARM 常见默认）；
- x86-64 等 char 有符号平台该问题不出现（上游 CI 因此全绿，平台差异类陷阱）。

## 反例与限制

- 禁止 `static_cast<char>(-1)` 显式转换掩盖——不改语义，模板分支仍按无符号推理；
- 禁止 `-Wno-c++11-narrowing` 关闭诊断——模板实参窄化仍是错误，非可忽略警告；
- 不适用 C 语言 char 符号性运行期问题（那属于 E419 / -fsigned-char 家族）。
