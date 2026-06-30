# E035: C++23 编译器不支持错误

## 错误特征

编译时出现以下错误：
```
error: no member named 'sort' in namespace 'std::ranges'
error: no member named 'find' in namespace 'std::ranges'
error: no member named 'reverse_view' in namespace 'std::ranges'
error: no member named 'contains' in 'std::string'
```

## 根因分析

软件要求 C++23 标准，但当前编译器（Clang 15.0.4）仅支持 C++20。

**典型案例**：poppler 从 25.12.0 开始切换到 C++23（参见 release notes）：
- CMakeLists.txt 中设置 `CMAKE_CXX_STANDARD=23`
- 源码大量使用 `std::ranges::sort`, `std::ranges::find`, `std::ranges::reverse_view`
- 使用 `std::string::contains` (C++23 新增)

## 解决方案

### 方案 1：升级编译器（推荐）

安装支持 C++23 的编译器：
- **Clang 16+** (完整支持 std::ranges)
- **GCC 12+** (支持大部分 C++23 特性)

### 方案 2：编译旧版本

编译使用 C++20 的旧版本：
- poppler 25.11.0 及更早版本使用 C++20
- 检查 CMakeLists.txt 中 `CMAKE_CXX_STANDARD` 的值

### 方案 3：手动降级（不推荐）

**风险极高**，涉及：
- `std::ranges::sort` → `std::sort(vec.begin(), vec.end(), comp)`
- `std::ranges::find` → `std::find(vec.begin(), vec.end(), val)`
- `std::ranges::reverse_view` → 无简单替代，需使用 `rbegin()/rend()`
- `std::string::contains` → `str.find(substr) != std::string::npos`

**成本**：poppler 26.05.0 涉及 16+ 个文件、40+ 处修改，且部分特性无简单替代。

## 检查命令

```bash
# 检查编译器版本
clang++ --version

# 检查是否支持 C++23
echo '#include <ranges>' | clang++ -std=c++23 -x c++ - -c -o /dev/null 2>&1
```

## 受影响软件

| 软件 | 版本范围 | C++ 标准 |
|------|----------|---------|
| poppler | 25.12.0+ | C++23 |
| poppler | ≤25.11.0 | C++20 |

## 参考资料

- poppler releases.html: 25.12.0 "Switch to C++23"
- C++23 status: https://en.cppreference.com/w/cpp/23
- Clang C++ status: https://clang.llvm.org/cxx_status.html