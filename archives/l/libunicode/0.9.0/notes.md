# libunicode 0.9.0 编译笔记

## 编译环境
- OpenHarmony SDK Clang 15.0.4 (aarch64-unknown-linux-ohos)
- C++20 标准，libc++ 运行时

## 遇到的问题与解决方案

### 1. std::format 不支持（Clang 15 限制）
**问题**: Clang 15 有 `<format>` 头文件但 `std::format`/`std::formatter` 未实现

**解决**:
- 创建 `format_compat.h` 自定义实现 `compat::format`
- 使用 `std_format` 宏替换 `std::format`
- 修改 tablegen 源码: `enum_generator.cpp`, `ucd_api_generator.cpp`, `case_norm_generator.cpp`

### 2. std::simd 不支持（Clang 15 限制）
**问题**: libc++ 不支持 `<simd>` 或 `stdx::simd`

**解决**:
- 配置时禁用 SIMD: `-DLIBUNICODE_SIMD_IMPLEMENTATION=none`

### 3. std::formatter 特化不支持
**问题**: emoji_segmenter.h 中有 std::formatter 特化，编译失败

**解决**:
- 移除 emoji_segmenter.h 中的 std::formatter 特化（仅 Catch2 测试需要，已禁用测试）

## 编译配置
```bash
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DLIBUNICODE_BUILD_STATIC=OFF \
  -DLIBUNICODE_TESTING=OFF \
  -DLIBUNICODE_TOOLS=OFF \
  -DLIBUNICODE_SIMD_IMPLEMENTATION=none \
  -DCMAKE_CXX_FLAGS="-stdlib=libc++" \
  -DCMAKE_EXE_LINKER_FLAGS="-stdlib=libc++ -lc++"
```

## 编译产物
- libunicode.so: 核心库
- libunicode_ucd.so: Unicode 数据库
- 头文件: ucd.h, ucd_enums.h, case_mapping.h 等

## 知识提取
- Clang 15 不支持 std::format，需使用自定义兼容层
- Clang 15 不支持 std::simd，需禁用 SIMD 实现
- Clang 15 不支持 std::formatter 特化，需移除 Catch2 测试相关代码
