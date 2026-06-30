# s2geometry - 球面几何计算库

## 软件概述

S2 Geometry Library 是 Google 开发的高性能球面几何计算库，专为处理球面坐标系上的几何运算而设计。该库提供了丰富的几何形状操作功能，包括点、线、多边形等形状的精确计算，支持空间索引、区域覆盖、距离计算等核心功能。S2 库广泛应用于地理信息系统（GIS）、地图应用、空间数据库等领域。

### 主要功能

1. **几何形状表示**：
   - S2Point：三维向量表示的球面点
   - S2Polyline：球面上的线段集合
   - S2Polygon：球面上的多边形区域
   - S2Cell：基于 S2 单元层级划分的几何单元

2. **几何计算**：
   - 球面距离计算（弧长、弦长）
   - 区域覆盖算法
   - 几何形状相交、包含、距离查询
   - 凸包计算、缓冲区生成

3. **空间索引**：
   - S2ShapeIndex：几何形状空间索引
   - 高效的近邻查询、范围查询
   - 支持动态添加和删除形状

4. **编码与压缩**：
   - 高效的几何形状编码
   - 数据压缩存储
   - 序列化与反序列化

### 应用场景

- 地理信息系统（GIS）
- 地图应用开发
- 空间数据库索引
- 位置服务
- 地理围栏
- 空间数据分析

## 版本信息

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 0.10.0 | ✅ built | 2026-06-17 | C++17 兼容 abseil-cpp 20240722.0 |

## 依赖关系

### 核心依赖

| 依赖 | 版本要求 | 说明 |
|------|----------|------|
| abseil-cpp | ≥ 20240722.0 | Google 基础库，C++17 要求 |
| OpenSSL | ≥ 1.1.1w | 加密相关功能支持 |

### 编译依赖

- cmake ≥ 3.12
- clang ≥ 15.0（或 GCC ≥ 9.0）
- C++17 标准支持

## 编译产物

### 0.10.0 版本

**库文件**：
- `lib/libs2.a` (3.5 MB) - 静态库

**头文件**（121 个）：
- `include/s2/*.h` - 核心几何类型头文件
- `include/s2/base/*.h` - 基础类型定义
- `include/s2/util/*.h` - 工具类和辅助函数

## 使用方法

### CMake 集成

s2geometry 不提供 CMake config 文件，需要手动配置：

```cmake
# 设置头文件和库路径
set(S2_INCLUDE_DIR "/path/to/usr/local/include")
set(S2_LIBRARY_DIR "/path/to/usr/local/lib")

# 添加到目标
include_directories(${S2_INCLUDE_DIR})
link_directories(${S2_LIBRARY_DIR})

target_link_libraries(your_target
    s2
    absl_strings absl_base absl_int128
    ssl crypto
)
```

### 手动编译示例

```cpp
#include "s2/s2point.h"
#include "s2/s2cell.h"
#include <iostream>

int main() {
    // 创建球面点
    S2Point point(1.0, 0.0, 0.0);

    // 获取对应的 S2 单元
    S2CellId cell_id = S2CellId::FromPoint(point);

    std::cout << "Cell ID: " << cell_id.id() << std::endl;
    return 0;
}
```

编译命令：
```bash
clang++ -std=c++17 your_code.cpp \
    -I/path/to/usr/local/include \
    -L/path/to/usr/local/lib \
    -ls2 -labsl_strings -labsl_base -labsl_int128 \
    -lcrypto -lssl
```

## 编译注意事项

1. **C++ 标准要求**：
   - 必须使用 C++17（不能使用 C++11/14）
   - abseil-cpp 20240722.0 需要 C++14+ 支持

2. **CMakeLists.txt 修改**：
   - 源码默认设置 C++11，需要手动修改为 C++17
   - 命令行 `-DCMAKE_CXX_STANDARD=17` 参数无效
   - 必须修改 CMakeLists.txt 第 22 行

3. **无 CMake Config 文件**：
   - 用户需要手动配置 include 和 lib 路径
   - 不提供 `find_package(s2geometry)` 支持

4. **静态库**：
   - 默认只编译静态库
   - 如需动态库，需设置 `BUILD_SHARED_LIBS=ON`

## 质量门禁状态

### 0.10.0 版本

| 门禁 | 状态 | 说明 |
|------|------|------|
| G0: 干净构建 | ✅ 通过 | 补丁自包含 |
| G1: 二进制完整性 | ✅ 通过 | libs2.a 3.5MB |
| G2: 功能可用性 | ✅ 通过 | 功能验证测试成功 |
| G3: 可移植性 | ✅ 通过 | ELF 格式正确 |
| G4: 档案完整性 | ✅ 通过 | 必填文件齐全 |

## 相关资源

- **官方网站**：https://github.com/google/s2geometry
- **文档**：https://s2geometry.io/
- **源码**：https://github.com/google/s2geometry
- **API 参考**：https://s2geometry.io/devguide/s2.html

## 更新历史

- **2026-06-17**: 编译 0.10.0 版本，修复 C++17 兼容性问题
- **2024-04-01**: 源码发布 v0.10.0 版本

---

**维护者**: openharmony-compile-agent
**最后更新**: 2026-06-17