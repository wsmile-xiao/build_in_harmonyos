# cctz

CCTZ (C++ Time Zone) 是一个用于在绝对时间（time_t / time_point）与民用时间（civil_time）之间进行转换的 C++ 库，使用时区规则进行计算。

## 功能描述

cctz 提供：
- `cctz::civil_time`: 表示人类尺度的日期和时间（年、月、日、时、分、秒）
- `cctz::time_zone`: 带有完整民用时间转换规则（如 DST）的时区对象
- 绝对时间（`time_point<seconds>`）与民用时间之间的双向转换函数
- 时间格式化（`format`）和解析（`parse`）函数
- 灵活的 `zone_info_source` 接口，用于提供时区数据

## 已编译版本

| 版本 | 状态 | 构建系统 | 测试结果 | 说明 |
|------|------|----------|----------|------|
| 2.5 | published | cmake | 10项全通过 | BUILD_TESTING=OFF（GTest/GMock 缺失），功能验证通过 |

## 产物说明

- **libcctz.a**: 静态库（280KB），包含核心时区转换功能
- **time_tool**: 命令行工具，用于查询和格式化时间信息
- **头文件**: time_zone.h, civil_time.h, civil_time_detail.h, zone_info_source.h
- **cmake 配置**: find_package(cctz) 支持

## 鸿蒙平台注意事项

1. 非UTC时区加载需要 zoneinfo 数据文件（鸿蒙默认缺少 `/usr/share/zoneinfo`）
2. CMake 配置时需设置 `BUILD_TESTING=OFF`（GTest/GMock 无预编译包）
3. CMake "System is unknown" 警告不影响编译和运行

## 依赖

- 无外部库依赖（仅需 pthread）
- 编译依赖: clang/cmake/make

## 链接方式

```cmake
find_package(cctz REQUIRED HINTS /path/to/usr/local/lib/cmake/cctz)
target_link_libraries(myapp cctz::cctz)
```

或直接链接静态库：
```bash
clang++ -std=c++11 myapp.cc -I/path/to/usr/local/include \
  /path/to/usr/local/lib/libcctz.a -pthread
```

## 链接

- 源码: https://github.com/google/cctz
- 许可证: Apache-2.0