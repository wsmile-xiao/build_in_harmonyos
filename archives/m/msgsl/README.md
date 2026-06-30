# msgsl (Microsoft Guidelines Support Library)

## 简介

Microsoft GSL (Guidelines Support Library) 是一个 header-only C++ 库，实现了 C++ Core Guidelines 中的类型和安全检查工具。它提供了 span、not_null、string_span 等实用类型，帮助编写更安全、更现代的 C++ 代码。

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 | 备注 |
|------|------|---------|--------|------|
| 4.0.0 | built | 2026-06-05 | 3 | CMake 版本兼容性修复 |

## 特性

- **Header-only**: 无需编译库文件，直接包含头文件即可使用
- **C++14+**: 支持 C++14 及更高版本标准
- **零依赖**: 不依赖第三方库（测试除外）
- **类型安全**: 提供 span、not_null 等安全类型
- **边界检查**: 支持数组边界检查（可配置）

## 主要组件

### gsl::span
- 类似 std::span 的视图类型
- 提供边界检查功能
- 支持静态和动态 extent

### gsl::not_null
- 空指针检查智能包装器
- 编译期和运行期检查
- 防止空指针解引用

### gsl::string_span
- 字符串视图类型
- 支持 ASCII 和宽字符
- 边界安全的字符串操作

### gsl::algorithm
- GSL 建议的算法实现
- 边界检查的拷贝和移动

### gsl::util
- 工具函数和类型
- finally、as_writeable_bytes 等

## 安装方法

### 使用预编译包（推荐）
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- msgsl 4.0.0
```

### 手动安装
```bash
tar -xzf msgsl-4.0.0-ohos-aarch64.tar.gz -C ~/usr/local
```

## 使用示例

### CMake 项目集成
```cmake
find_package(Microsoft.GSL REQUIRED)
target_link_libraries(your_target PRIVATE Microsoft.GSL::GSL)
```

### 直接包含头文件
```cpp
#include <gsl/gsl>  // 包含所有 GSL 类型

// 使用 span
void process_data(gsl::span<int> data) {
    for (auto& elem : data) {
        // 边界安全的访问
        elem *= 2;
    }
}

// 使用 not_null
void process_ptr(gsl::not_null<int*> ptr) {
    *ptr = 42;  // 保证非空
}

// 使用 finally
void cleanup() {
    auto cleanup_action = gsl::finally([]() {
        // 清理代码
    });
    // 即使异常也会执行清理
}
```

## 编译说明

### 构建系统
- **类型**: CMake
- **编译器**: Clang 15.0.4
- **标准**: C++14 最低要求

### 编译选项
- `GSL_INSTALL`: 生成安装目标（默认 ON）
- `GSL_TEST`: 构建测试（默认 ON，建议 OFF）
- `CMAKE_INSTALL_PREFIX`: 安装路径（建议 ~/usr/local）

### 已知问题与修复

#### 版本 4.0.0 补丁说明

1. **CMake 版本兼容性**
   - **问题**: CMake 4.1.2 不支持 `cmake_minimum_required(VERSION < 3.5)`
   - **修复**: 更新所有 CMakeLists.txt 文件至 VERSION 3.5
   - **补丁**: 0001-CMakeLists.txt.patch, 0002-tests-CMakeLists.txt.patch, 0003-tests-CMakeLists.txt.in.patch

2. **测试下载限制**
   - **问题**: GoogleTest 网络下载失败
   - **方案**: 使用 `-DGSL_TEST=OFF` 禁用测试
   - **影响**: 无功能影响，header-only 库无需运行测试

### 编译流程
```bash
# 初始化
ohc-run.py init-build msgsl 4.0.0 --no-download --url=...

# 配置（禁用测试）
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DGSL_TEST=OFF

# 构建（无实际编译，仅生成安装目标）
make

# 安装
make install DESTDIR=~/test-install-msgsl-4.0.0

# 打包
ohc-run.py package msgsl 4.0.0

# 收尾
ohc-run.py finish msgsl 4.0.0 built
```

## 依赖关系

### 构建依赖
- **CMake**: 3.5+ (实际要求 4.1.2+)
- **C++ 编译器**: Clang 15.0.4 / GCC 9+

### 运行依赖
- **无**: Header-only 库，无运行时依赖

### 可选依赖
- **GoogleTest**: 仅测试时需要（编译时可禁用）

## 平台支持

- ✅ OpenHarmony (OHOS) aarch64
- ✅ Linux x86_64 / aarch64
- ✅ macOS
- ✅ Windows (MSVC)

## 许可证

MIT License

## 相关链接

- 官方仓库: https://github.com/microsoft/GSL
- C++ Core Guidelines: https://isocpp.github.io/CppCoreGuidelines/
- 文档: https://github.com/microsoft/GSL/blob/main/README.md

---
最后更新: 2026-06-05
维护者: OpenHarmonyPCDeveloper