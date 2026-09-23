# kodi-tools 21.3 适配笔记

## 结论
**适配成功**：conan-verify G0-G4 全部 PASS，状态 published。

## 软件包性质
kodi-tools 不是独立软件包，而是从 kodi 21.3-Omega 主项目中提取的两个工具：
- TexturePacker（tools/depends/native/TexturePacker/src）
- JsonSchemaBuilder（tools/depends/native/JsonSchemaBuilder/src）

## 关键修复记录（按遇到顺序）

1. **CMake 找不到 Conan 依赖**：CMakeLists.txt 用 `find_package(PNG/JPEG/GIF/Lzo2)`
   系统模块名。补丁改为 `find_package(libpng/libjpeg/giflib/lzo)` 并直接链接
   Conan targets（libpng::libpng 等），配合 conanfile 的 CMakeDeps 生成器。

2. **ENABLE_STATIC 陷阱**：原配方设 ENABLE_STATIC=ON，会把
   CMAKE_FIND_LIBRARY_SUFFIXES 限制为 .a，而 Conan 依赖是 .so →
   "Library 'png16'/'gif' not found"。必须去掉该变量。

3. **giflib 版本检查**：`file(STRINGS ${GIF_INCLUDE_DIR}/gif_lib.h)` 依赖
   FindGIF 模块变量，Conan 下为空/生成器表达式 → 直接删除该检查段
   （Conan 的 giflib 5.2.2 必然 ≥5）。

4. **TARGET_POSIX 宏**：cmdlineargs.h 无 TARGET_POSIX 时 include windows.h。
   CMakeToolchain 加 `preprocessor_definitions["TARGET_POSIX"]="1"`。

5. **两个 CMake 项目共用 build 目录冲突**：TexturePacker 构建后 CMakeCache
   记录了源目录，JsonSchemaBuilder configure 被拒。构建 jsb 前
   rmdir CMakeFiles + 删 CMakeCache.txt。

6. **test_package 运行**：不能用裸命令名（PATH 不含 bin），用
   `self.dependencies["kodi-tools"].cpp_info.bindirs[0]` 拼绝对路径；
   两工具打印 usage 后退出码非零，用 `|| true` 容错。

7. **libpng/1.6.58.2 可用**：之前判断其有 cpp_info 缺陷是误诊——
   真正根因是 ENABLE_STATIC 的 .a 后缀限制。

## 依赖
lzo/2.10, libpng/1.6.58.2, giflib/5.2.2, libjpeg/10（全部 OHOS armv8 二进制）
