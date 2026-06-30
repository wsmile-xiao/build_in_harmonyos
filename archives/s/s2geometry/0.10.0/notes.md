# s2geometry 0.10.0 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-06-17
- 编译器: clang 15.0.4
- 状态: **built** ✅

## 依赖版本
- **abseil-cpp**: 20240722.0（手动编译，兼容鸿蒙）
- **OpenSSL**: 1.1.1w（预安装）
- **cmake**: 4.1.2
- **clang**: 15.0.4

---

## 编译步骤（成功）

### 1. 初始化编译环境
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build s2geometry 0.10.0 \
  --url=https://github.com/google/s2geometry/archive/refs/tags/v0.10.0.tar.gz

source .build-context-s2geometry-0.10.0
```

### 2. 验证 abseil-cpp 安装
```bash
# 检查头文件
ls ~/usr/local/include/absl/ | head -10

# 检查库文件
ls ~/usr/local/lib/libabsl_*.a | wc -l  # 90 个

# 验证 CMake 配置
ls ~/usr/local/lib/cmake/absl/
```

### 3. CMake 配置（关键修改）
由于 s2geometry CMakeLists.txt 默认设置 C++11，而 abseil-cpp 20240722.0 需要 C++14+，需要修改源码：

**修改前**（CMakeLists.txt 第 22-25 行）：
```cmake
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
```

**修改后**：
```cmake
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
```

**重要发现**：命令行参数 `-DCMAKE_CXX_STANDARD=17` 无法覆盖 CMakeLists.txt 内的 `set(CMAKE_CXX_STANDARD 11)`！

CMake 配置命令：
```bash
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DWITH_GFLAGS=OFF \
  -DOPENSSL_ROOT_DIR=$DEFAULT_PREFIX
```

### 4. 编译
```bash
make -j$(nproc)
```
结果：编译成功，生成 `libs2.a` (3.5 MB)

### 5. 安装
```bash
# Staging 安装
make install DESTDIR=$TEST_PREFIX

# 本地安装
make install
```

### 6. 功能验证
```cpp
#include "s2/s2point.h"
#include <iostream>

int main() {
    S2Point point(1.0, 0.0, 0.0);
    std::cout << "S2Point created: x=" << point.x() << std::endl;
    return 0;
}
```

编译和运行：
```bash
clang++ -std=c++17 test-s2.cpp \
  -I~/usr/local/include -L~/usr/local/lib \
  -ls2 -labsl_strings -labsl_base -labsl_int128 \
  -o test-s2

./test-s2  # 输出: S2Point created: x=1
```

---

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake C++ 标准未生效 | CMakeLists.txt 内的 `set()` 覆盖命令行参数 | 修改 CMakeLists.txt 第 22 行 |
| 2 | OpenSSL 未找到 | 未设置 OPENSSL_ROOT_DIR | 添加 `-DOPENSSL_ROOT_DIR=$DEFAULT_PREFIX` |
| 3 | 编译错误：C++14 not supported | 编译器实际使用 C++11 | 修改 CMakeLists.txt 强制 C++17 |

---

## 补丁详情

### 补丁文件：0001-CMakeLists.txt.patch

修改 CMakeLists.txt，将 C++ 标准从 11 提升到 17，以兼容 abseil-cpp 20240722.0。

---

## 交付物清单

### 库文件
- `lib/libs2.a` (3.5 MB) - 静态库

### 头文件（121 个）
- `include/s2/*.h` - 核心头文件
- `include/s2/base/*.h` - 基础类型
- `include/s2/util/bits/*.h` - 位操作工具
- `include/s2/util/coding/*.h` - 编码工具
- `include/s2/util/endian/*.h` - 字节序处理
- `include/s2/util/gtl/*.h` - 泛型容器
- `include/s2/util/hash/*.h` - 哈希工具
- `include/s2/util/math/*.h` - 数学工具
- `include/s2/util/units/*.h` - 单位转换

---

## 使用说明

### CMake 集成
s2geometry **不提供** CMake config 文件，需手动指定路径：

```cmake
# 在 CMakeLists.txt 中添加
include_directories(/path/to/usr/local/include)
link_directories(/path/to/usr/local/lib)

target_link_libraries(your_target
  s2
  absl_strings absl_base absl_int128
  openssl
)
```

### 手动编译
```bash
clang++ -std=c++17 your_code.cpp \
  -I/path/to/usr/local/include \
  -L/path/to/usr/local/lib \
  -ls2 -labsl_strings -labsl_base -labsl_int128 \
  -lcrypto
```

---

## 关键依赖说明

### abseil-cpp 版本要求
- **必须使用**: 20240722.0 或更高版本
- **编译要求**: C++17 标准
- **原因**: abseil 20240722.0 需要 C++14+ 支持

### 依赖链接顺序
链接 s2geometry 时，需按以下顺序链接 abseil 库：
1. `-labsl_strings`
2. `-labsl_base`
3. `-labsl_int128`
4. 其他 abseil 库（根据需要）

---

## 注意事项

1. **C++ 标准必须是 17**：不能使用 C++11 或 C++14
2. **命令行参数无效**：必须修改 CMakeLists.txt
3. **无 CMake config**：用户需手动配置路径
4. **静态库**：默认编译静态库，无动态库版本
5. **测试未运行**：未配置 GTEST_ROOT

---

**编译完成**: 2026-06-17
**最终状态**: built ✅
**关键突破**: 修改 CMakeLists.txt 将 C++11 改为 C++17