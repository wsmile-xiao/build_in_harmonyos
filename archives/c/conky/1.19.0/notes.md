# conky 1.19.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. **源码下载与解压**
   ```bash
   wget https://github.com/brndnmtthws/conky/archive/refs/tags/v1.19.0.tar.gz
   tar -xzf v1.19.0.tar.gz
   cd conky-1.19.0
   ```

2. **CMake 配置**
   ```bash
   cmake -B build \
     -DCMAKE_BUILD_TYPE=Release \
     -DBUILD_X11=OFF \
     -DBUILD_WAYLAND=OFF \
     -DBUILD_IMLIB2=OFF \
     -DBUILD_I18N=OFF \
     -DCMAKE_SYSTEM_NAME=OHOS \
     -DCMAKE_C_COMPILER=clang \
     -DCMAKE_CXX_COMPILER=clang++
   ```

3. **编译构建**
   ```bash
   cd build
   make -j$(nproc)
   ```

4. **安装打包**
   ```bash
   make install DESTDIR=install
   tar -czf conky-1.19.0-ohos-aarch64.tar.gz -C install .
   ```

5. **验证测试**
   ```bash
   conky --version
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 条件编译错误 | X11/Wayland 宏定义冲突 | 添加 0001-fix-cmake-conditional-compilation.patch，修复 CMakeLists.txt 条件判断 |
| 2 | getutline 未定义 | OpenHarmony 缺少 utmpx.h 函数 | 添加 0002-fix-getutline-missing.patch，实现 getutline 兼容函数 |
| 3 | X11/Wayland 初始化失败 | 缺少图形子系统支持 | 添加 0003-fix-x11-wayland-init.patch，禁用图形相关初始化代码 |
| 4 | lua 头文件路径错误 | OpenHarmony lua 安装路径非标准 | CMake 配置时指定 LUA_INCLUDE_DIR 和 LUA_LIBRARY |
| 5 | ncursesw 链接失败 | 未正确链接 ncursesw 库 | CMake 配置时指定 CMAKE_REQUIRED_LIBRARIES 添加 ncursesw |

## 源码修改

### 0001-fix-cmake-conditional-compilation.patch
修复 CMakeLists.txt 中 X11 和 Wayland 的条件编译逻辑，避免在禁用图形支持时出现编译错误。

### 0002-fix-getutline-missing.patch
为 OpenHarmony 实现兼容的 getutline 函数，解决 utmpx.h 函数缺失问题。

### 0003-fix-x11-wayland-init.patch
禁用 X11/Wayland 初始化代码路径，避免在无图形子系统环境下运行时崩溃。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| lua | 5.3.6 | 脚本引擎 |
| ncursesw | 6.4 | 终端界面库（宽字符版本） |

## 验证结果

```bash
# 版本验证
$ conky --version
conky 1.19.0
Compiled Wed May 26 19:48:00 CST 2026 for Linux

# 基本功能测试
$ conky -C  # 配置文件语法检查
$ conky -v  # 详细版本信息
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conky-1.19.0-ohos-aarch64.tar.gz | 5.8M | OpenHarmony aarch64 预编译包 |
| 0001-fix-cmake-conditional-compilation.patch | 955B | CMake 条件编译修复 |
| 0002-fix-getutline-missing.patch | 756B | getutline 兼容性补丁 |
| 0003-fix-x11-wayland-init.patch | 766B | X11/Wayland 初始化修复 |

## 注意事项

1. **禁用图形支持**：由于 OpenHarmony aarch64 缺少 X11/Wayland 图形子系统，编译时必须禁用相关功能（`-DBUILD_X11=OFF -DBUILD_WAYLAND=OFF`）

2. **国际化支持**：I18N 支持已禁用（`-DBUILD_I18N=OFF`），如有需要需额外处理

3. **运行环境**：需要确保 lua 5.3.6 和 ncursesw 6.4 已正确安装到目标系统

4. **补丁依赖**：三个补丁必须按顺序应用，顺序错误可能导致编译失败

## 编译结束

- 编译完成时间: 2026-05-26 19:48
- 最终状态: published
- 归档完整性: 已通过 G4 门禁检查