# E103: C++17 Structured Binding Lambda Capture Error

## 错误表现

```
error: 'dirStr' in capture list does not name a variable
auto process = [this, cmd, dirStr]() -> size_t
                         ^
note: 'dirStr' declared here
for (const auto &[dirStr, jobs] : byDir)
                  ^
```

## 根本原因

C++17 structured binding 引入的变量名（如 `dirStr`）实际上是隐藏的引用或别名，编译器内部将其映射到绑定对象的成员。这些隐藏变量不能直接在 lambda 捕获列表中使用，因为捕获列表要求明确的变量名。

**技术细节**：
- Structured binding 展开为类似 `auto __hidden1 = byDir.first; auto& dirStr = __hidden1;`
- `dirStr` 是引用别名，不是独立变量
- Lambda 捕获列表要求捕获独立变量，不能捕获别名

## 受影响场景

常见于：
1. 遍历 `std::map` / `std::unordered_map` 后在 lambda 中使用 key/value
2. 遍历 `std::pair` 数组后在 lambda 中使用 first/second
3. 遍历自定义结构体的 structured binding

示例：
```cpp
for (const auto &[key, value] : map) {
    auto process = [key, value]() { ... }; // 错误！
}
```

## 解决方案

在 lambda 捕获前创建局部变量副本：

```cpp
for (const auto &[key, value] : map) {
    std::string keyCopy = key;
    int valueCopy = value;
    auto process = [keyCopy, valueCopy]() { ... }; // 正确
}
```

## 实际案例

**doxygen 1.17.0** `src/dotrunner.cpp:400`：

```cpp
// 错误代码
for (const auto &[dirStr, jobs] : byDir) {
    auto process = [this, cmd, dirStr]() -> size_t { // 错误！
        err_full(..., dirStr, ...);
    };
}

// 修复后
for (const auto &[dirStr, jobs] : byDir) {
    std::string dirStrCopy = dirStr; // 创建副本
    auto process = [this, cmd, dirStrCopy]() -> size_t { // 捕获副本
        err_full(..., dirStrCopy, ...); // 使用副本
    };
}
```

## 编译器差异

- **Clang 15+**: 明确报错 "capture list does not name a variable"
- **GCC 10+**: 同样报错，但错误信息略有不同
- **C++20**: 允许捕获 structured binding（需要 `const auto& [...args] = ...`）

## 验证方法

```bash
# 编译包含 structured binding + lambda 的代码
clang++ -std=c++17 test.cpp

# 应无错误输出
```

## 参考资料

- [C++17 Structured Bindings](https://en.cppreference.com/w/cpp/language/structured_binding)
- [Lambda Captures](https://en.cppreference.com/w/cpp/language/lambda#Captures)
- [P0588R1: Simplifying structured bindings](http://www.open-std.org/jtc1/sc22/wg21/docs/papers/2017/p0588r1.html)