# libc++ ABI 命名空间 `__n1` 出现在 typeid 反解类型名中，类型名规范化需剥离

- **类别**: platform, libcxx-stdlib, compatibility, type-name
- **构建系统**: cmake | clang | clang++
- **阶段**: runtime | testing

## 错误特征

```
SimTK Exception thrown at TestNiceTypeName.cpp:278:
  Assertion '((NiceTypeName<std::vector<int>>::namestr()
  == "std::vector<int,std::allocator<int>>"))' failed.
```

typeid 反解原始输出：

```
mangled:   NSt4__n16vectorIiNS_9allocatorIiEEEE
demangled: std::__n1::vector<int, std::__n1::allocator<int>>
```

## 根因

OHOS SDK 的 clang15/libc++ 使用 `__n1` 作为 ABI 内联命名空间。依赖
`typeid().name()` + `abi::__cxa_demangle` 做类型名规范化的库，只剥离了 OSX
clang 的 `__[0-9]+::`（如 `__1`），未覆盖 `__n1`，导致规范化结果仍含
`std::__n1::` 前缀，与期望字符串（如 `std::vector<int,std::allocator<int>>`）
不一致。

## 方案

在类型名规范化函数中增加 `\b__n[0-9]+::` 剥离规则（libc++ ABI 内联命名空间
通用形态 `__n<n>`）：

```cpp
// OSX clang throws in extra namespaces like "__1". Delete them.
SPair(std::regex("\\b__[0-9]+::"),  ""),
// libc++ ABI namespace on HarmonyOS/OHOS is "__n1" (e.g. std::__n1::vector).
SPair(std::regex("\\b__n[0-9]+::"), ""),
```

注意若使用 `std::array<SPair,N>` 静态数组，需要同步把 N 从 7 改为 8。

## 验证

- 修改前: `TestNiceTypeName` FAIL（0.03s 内断言失败）
- 修改后: `TestNiceTypeName` PASS；全套上游测试 113/113 通过
- conan create（ohos-aarch64）+ test_package 消费者测试 PASS

## 适用边界 / 反例

- **适用**: 运行在 OHOS/HarmonyOS（clang15/libc++，ABI 命名空间 `__n1`）上、
  依赖 typeid 反解类型名并做字符串规范化的 C++ 库（类型名反射、序列化、日志等）。
- **反例**: 不基于 `__cxa_demangle` 的编译期类型名（`__PRETTY_FUNCTION__`
  与宏展开）不受影响；`__n1` 前缀若出现在**链接符号**场景（如 E247 的
  `undefined symbol: std::__n1::operator new`）属于 pkg-config 缺 C++ 运行时
  问题，与本条类型名规范化场景不同。

## 关联

- `similar_to`: E247（std::__n1 出现在链接符号场景）
- `caused_by`: OHOS SDK clang15/libc++ 的 ABI 内联命名空间 `__n1`
- 实测案例: simbody 3.8（SimTKcommon NiceTypeName，补丁
  0002-SimTKcommon-src-NiceTypeName.cpp.patch）
