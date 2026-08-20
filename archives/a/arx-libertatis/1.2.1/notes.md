# arx-libertatis 1.2.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-19
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤

### 1. Conan 依赖安装
```bash
# 创建 conanfile.txt 并安装依赖
conan install . -pr:b=ci/conan/profiles/ohos-aarch64 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing
```

### 2. CMake 配置
```bash
# 不使用 conan 工具链（CMakeDeps 变量作用域问题），直接设置 CMAKE_PREFIX_PATH
cmake -B cmake-build -S . \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=$TEST_PREFIX \
  -DCMAKE_PREFIX_PATH="<conan_pkg_dirs>" \
  -DCMAKE_C_FLAGS="-fPIC -O2 -include ohos_stubs.h" \
  -DCMAKE_CXX_FLAGS="-fPIC -O2 -include ohos_stubs.h" \
  -DUSE_OPENAL=OFF -DUSE_X11=OFF -DUSE_NATIVE_FS=ON \
  -DBUILD_CRASHHANDLER=OFF -DBUILD_PROFILER=OFF -DBUILD_TESTS=OFF \
  -DINSTALL_BLENDER_PLUGIN=OFF -DBUILD_IO_LIBRARY=ON -DBUILD_TOOLS=ON \
  -DSTRICT_USE=OFF -DUSE_STATIC_LIBS=OFF -DUSE_LTO=OFF \
  -DICON_TYPE=none -DDATA_FILES="" -DOPTIMIZE_ICONS=OFF
```

### 3. 构建（部分适配）
```bash
cmake --build cmake-build --target ArxIO -- -j1
cmake --build cmake-build --target arxtool -- -j1
```

### 4. 安装
```bash
cp cmake-build/libArxIO.so* $TEST_PREFIX/lib/
cp cmake-build/arxtool $TEST_PREFIX/libexec/
ln -sf ../libexec/arxtool $TEST_PREFIX/bin/arxsavetool
ln -sf ../libexec/arxtool $TEST_PREFIX/bin/arxunpak
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMakeDeps 变量作用域问题 | conandeps_legacy.cmake 在 toolchain 中调用 find_package，变量在 toolchain 作用域设置后不传播到主 CMakeLists.txt | 不使用 conan 工具链，直接设置 CMAKE_PREFIX_PATH 让自定义 Find 模块通过 find_path/find_library 搜索 |
| 2 | check_link_library 失败 (boost::boost) | Conan CMakeDeps 返回 imported target 名称，Arx 的 try_compile 测试无法解析 | 注释 CMakeLists.txt 中的 check_link_library(Boost) 调用 |
| 3 | Epoxy/GLM 未检测到 | CMakeDeps 设置小写 epoxy_FOUND/glm_FOUND，Arx 代码检查大写 EPOXY_FOUND/GLM_INCLUDE_DIRS | 在 project() 后添加变量映射块，将小写转为大写 |
| 4 | Inkscape 未找到 | ICON_TYPE 默认 iconset 需要 Inkscape 生成图标 | 设置 ICON_TYPE=none |
| 5 | SDL2 未找到导致 fatal error | 无 SDL2 依赖，主游戏二进制无法构建 | 将 SEND_ERROR 改为 WARNING，仅构建 IO 库和工具 |
| 6 | pthread_setcancelstate 未声明 | OHOS 不支持 pthread_cancel 相关函数 | 创建 ohos_stubs.h 提供 no-op stub，通过 -include 全局注入 |
| 7 | ft2build.h 未找到 | CMakeDeps Freetype 变量作用域问题 | 同问题1解决方案 |
| 8 | zlib 版本冲突 | boost/1.84.0 需 zlib/1.3.1, libpng 需 zlib/1.3.1.1 | 仅声明直接依赖（zlib/1.3.1），让 conan 解析传递依赖 |

## 源码修改

### CMakeLists.txt
1. **注释 check_link_library(Boost)**: 第 ~512 行，`# check_link_library(Boost Boost_LIBRARIES)` — Conan CMakeDeps 返回 imported target 不兼容 try_compile
2. **注释 check_link_library(Epoxy)**: 第 ~435 行，同上原因
3. **添加 Conan 变量映射块**: project() 后，将小写 conan 变量映射到大写 (zlib_INCLUDE_DIRS→ZLIB_INCLUDE_DIRS 等)
4. **SDL 错误降级**: 将 `SEND_ERROR "No windowing backend available"` 改为 `WARNING`
5. **Epoxy 检测增强**: 添加 find_path/find_library 回退检测

### ohos_stubs.h (新文件)
提供 `pthread_setcancelstate` 的 no-op 实现，解决 boost smart_ptr 头文件在 OHOS 上的编译错误。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| zlib | 1.3.1 | Conan |
| freetype | 2.14.3 | Conan |
| boost | 1.84.0 | Conan |
| glm | 0.9.9.8 | Conan (header-only) |
| libepoxy | 1.5.10 | Conan |
| SDL2 | N/A | 不可用（archives 有记录但未发布到制品仓） |
| OpenAL | N/A | 不可用 |

## 验证结果

```bash
# 构建产物 ELF 检查
$ file lib/libArxIO.so.1.2.1
ELF shared object, 64-bit LSB arm64, not stripped

$ file libexec/arxtool
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libArxIO.so.1.2.1 | Arx 数据读写共享库 |
| lib/libArxIO.so.0 | SO ABI 版本链接 |
| lib/libArxIO.so | 开发链接 |
| libexec/arxtool | 数据工具（savetool/unpak 合并） |
| bin/arxsavetool | 存档工具（符号链接到 arxtool） |
| bin/arxunpak | 解包工具（符号链接到 arxtool） |

## 注意事项

1. **部分适配**：由于 SDL2 和 OpenAL 不可用，主游戏二进制（arx）未构建。仅构建了 IO 库（libArxIO.so）和工具（arxtool）。
2. **OHOS 平台限制**：`pthread_setcancelstate` 在 OHOS 上不可用，通过 ohos_stubs.h 提供无操作 stub。
3. **CMakeDeps 兼容性**：Arx 的自定义 Find 模块（FindEpoxy.cmake, FindGLM.cmake）与 Conan CMakeDeps 存在变量命名冲突（大小写不匹配），通过不使用 conan 工具链、直接设置 CMAKE_PREFIX_PATH 绕过。
4. **CMAKE_SYSTEM_NAME=Linux**：OHOS 不被 CMake 识别，设置为 Linux 进行交叉编译。
5. **USE_NATIVE_FS=ON**：使用 POSIX 文件系统后端，避免 boost::filesystem 依赖。
---

**编译结束**: 2026-08-19 12:00
**最终状态**: built
