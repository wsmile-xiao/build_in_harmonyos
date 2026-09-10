# E544 草稿：OHOS libc++ 无 C++20 ranges 算法 + conan cppstd 块压制 ECM C++20

## 现象

baloo 6.28.0（src/engine 用 std::ranges::any_of）在 OHOS 上两轮报错：
1. first: no member named 'ranges' in namespace 'std'（-std=c++17 生效）
2. 修正 flags 后: no member named 'any_of' in namespace 'std::ranges'
   （c++20 生效但 libc++ 无算法实现）

## 根因

1. conan toolchain cppstd=17 的三重压制（普通变量 + variable_watch + cache
   不生效），使 ECM KDECompilerSettings 跳过自设 20 且 CMake 追加 -std=c++17。
2. OHOS clang 15 libc++ 没有 C++20 ranges 算法（any_of/find_if 皆缺），
   <ranges> 头与经典算法可用。

## 修复（双修）

```python
def generate(self):
    tc = CMakeToolchain(self)
    tc.blocks.remove("cppstd")   # 让 ECM 自设 C++20
    ...
```

+ 补丁把 ranges 调用换成经典算法：

```cpp
// before
if (std::ranges::any_of(m_iterators, [](const auto &e) { ... }))
// after
if (std::any_of(m_iterators.cbegin(), m_iterators.cend(), [](const auto &e) { ... }))
```

baloo 6.28.0 实测：blocks.remove + 3 处补丁后 33 项测试全量编译通过。
