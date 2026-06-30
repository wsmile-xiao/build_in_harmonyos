# libdjinterop
C++ library providing access to DJ record libraries (Engine Library format).

## Supported Features
- Track metadata, beat grids, hot cues, loops, waveforms
- Engine Library v1/v2/v3 database formats
- SC5000 firmware 1.0.3 to 4.1.0
- Engine DJ Desktop 1.0.1 to 4.1.0

## Project URL
https://github.com/xsco/libdjinterop

## License
LGPL-2.1-or-later

## HarmonyOS 适配说明

### 构建信息
- **版本**: 0.24.3-r1
- **构建系统**: cmake
- **编译器**: clang 15.0.4 / clang++ 15.0.4
- **状态**: published (2026-06-02)
- **编译类型**: 静态库 (BUILD_SHARED_LIBS=OFF)

### 依赖
- zlib 1.3.1 (预编译包)
- sqlite3 3.49.1 (预编译包)

### 补丁
- `0001-CMakeLists.txt.patch`: 3 夘修改
  1. 移除 `-Werror` 编译选项
  2. pkg-config 条件: `UNIX` → `UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"`
  3. 测试代码用 `BUILD_TESTING=OFF` 条件守卫 (Boost pthread_setcancelstate 不可用)

### 平台限制
| 限制 | 影响 | 解决方案 |
|------|------|----------|
| /tmp 只读 | sqlite3 临时文件创建 | TMPDIR=$HOME/tmp |
| pthread_setcancelstate 缺失 | Boost 测试框架不可用 | BUILD_TESTING=OFF |
| CMake 不识别 HarmonyOS | pkg-config 不生成 | 补丁适配条件判断 |

### 验证结果
- 质量门禁 G0-G4: ✅ PASS (G0 手动验证)
- C++ API: ✅ create_database/tracks/schema_version/uuid 验证通过
- pkg-config: ✅ modversion=0.24.3, libs/cflags 正确
- CMake find_package: ✅ DjInteropConfig.cmake 正常

### 使用方式
```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libdjinterop 0.24.3-r1

# C++ 链接 (需 C++20)
clang++ -std=c++20 your_program.cpp \
  $(pkg-config --libs --cflags djinterop) -lm -o your_program

# CMake find_package
find_package(DjInterop REQUIRED)
target_link_libraries(your_target DjInterop)
```

### 注意事项
- 编译为静态库，需 C++20 编译器支持
- 用户代码需设置 `TMPDIR=$HOME/tmp` 避免 /tmp 只读问题
- 单元测试因 Boost 不可用而禁用，待 Boost 适配后可重新启用