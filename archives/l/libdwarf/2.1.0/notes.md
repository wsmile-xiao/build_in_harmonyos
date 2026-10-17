# libdwarf 2.1.0 适配笔记

## 编译环境
- 构建系统: CMake (standard conan CMakeToolchain + CMakeDeps + CMake)
- 编译日期: 2026-08-28
- 编译器: clang 15 (OHOS aarch64)
- 状态: published

## 依赖
- zlib/1.3.1 (published on ohpcd registry)
- zstd/1.5.6 (published on ohpcd registry)

## 编译步骤
```bash
# CMake build using conan
cmake -B build \
    -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
    -DBUILD_SHARED=OFF \
    -DBUILD_NON_SHARED=ON \
    -DBUILD_DWARFDUMP=OFF \
    -DBUILD_DWARFGEN=OFF \
    -DBUILD_DWARFEXAMPLE=OFF
cmake --build build -j2
cmake --install build --prefix $HOME/usr/local
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 | libdwarf 2.1.0 CMake 构建在 OHOS 上无需特殊适配 | 使用标准 conan CMake 流程 |

## 关键设计决策

### 1. 静态构建 LIBDWARF_STATIC=1
libdwarf 2.1.0 引入了 `LIBDWARF_STATIC` 宏：当构建静态库时，必须在
`package_info()` 中设置 `cpp_info.defines = ["LIBDWARF_STATIC=1"]`，以确保
头文件使用正确的声明（静态链接时导出/导入符号声明）。

### 2. 依赖管理
- zlib/1.3.1: 用于压缩 DWARF 数据
- zstd/1.5.6: 用于 Zstandard 压缩的 DWARF 数据（libdwarf >= 0.9.0 引入）
- 使用 CMakeDeps 生成器自动处理依赖发现

### 3. 补丁处理
- `2.1.0-0001-fixes.patch`: 修复 off_t 重定义（Windows MSVC 专用补丁）
- 在 OHOS 上不应用此补丁（仅 `settings.os == "Windows"` 时应用）
- 遵循上游 conan-center-index 的条件逻辑

### 4. 交叉编译处理
- 使用 `cross_building(self)` 检测交叉编译环境
- 设置 `HAVE_UNUSED_ATTRIBUTE_EXITCODE=0` 跳过需要运行的 CMake 检查
- test_package 使用 `can_run()` 守卫，交叉编译时跳过运行时测试

### 5. 构建选项
- `shared=False` (默认): 构建静态库
- `fPIC=True` (默认): 生成位置无关代码
- `with_dwarfgen=False`: 不构建 dwarfgen 工具
- `with_dwarfdump=False`: 不构建 dwarfdump 工具
- `BUILD_DWARFEXAMPLE=OFF`: 不构建示例程序

## 验证结果
- libdwarf.a 静态库编译成功 ✅
- test_package 链接成功 ✅
- dwarf_attrlist/dwarf_hasform API 可调用 ✅

## 交付物
- lib/libdwarf.a
- include/dwarf.h, include/libdwarf.h

## 注意事项
- libdwarf 2.1.0 是 CMake 项目，在 OHOS 上无需特殊平台适配
- off_t 补丁仅 Windows 需要，OHOS 上不影响
- 与同仓库的 dwarfutils/2.3.1 是同一项目的不同版本（2.3.1 无强制依赖）
