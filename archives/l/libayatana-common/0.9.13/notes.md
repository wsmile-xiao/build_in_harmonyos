# libayatana-common 0.9.13 — 适配笔记

## 编译环境
- 构建系统: cmake（上游顶层 CMakeLists.txt）
- 编译日期: 2026-08-27
- 编译器: clang/clang++ (15.0.4 OHOS toolchain)
- 目标: aarch64-linux-ohos (OHOS 6.0, armv8)

## 依赖
- glib/2.88.0.1（utils.h 直接包含 glib.h / glib-object.h / gio/gio.h，
  需透传头文件与库：`requires("glib/2.88.0.1", transitive_headers=True, transitive_libs=True)`）

## OHOS 适配要点

1. **跳过 data/ 与 po/ 子目录**（0001-skip-data-po-subdirs.patch）：
   - data/CMakeLists.txt `find_package(GSettings REQUIRED)` —— OHOS 无 GSettings CMake 模块
   - po/CMakeLists.txt `find_package(Intltool REQUIRED)` —— OHOS 无 Intltool CMake 模块
   - 新增 `SKIP_DATA_PO` CMake option 控制跳过

2. **测试裁剪**：上游测试依赖 GMock/Vala/GObjectIntrospection，OHOS 不可用
   → `ENABLE_TESTS=OFF` / `ENABLE_WERROR=OFF` / `ENABLE_LOMIRI_FEATURES=OFF`

3. **SONAME 修复**（0002-soname-link-flag.patch）：
   - 上游 src/CMakeLists.txt 硬编码 `add_library(ayatana-common SHARED ...)`，
     且 `SOVERSION ${ABI_VERSION}` 中 ABI_VERSION=0 → CMake 对 SOVERSION=0
     不生成 DT_SONAME
   - W3 L5 门禁要求共享库必须有 DT_SONAME（下游链接器按 SONAME 寻址）
   - 修复：set_target_properties 增加 `LINK_FLAGS "-Wl,-soname,libayatana-common.so"`
   - ⚠️ 不能用 conanfile 的 CMAKE_SHARED_LINKER_FLAGS/CONAN_SHARED_LINKER_FLAGS
     注入（toolchain 定义时序问题实测不生效；直接覆盖还会丢 -L 路径）

4. **依赖库搜索路径修复**（0003-link-deps-library-dirs.patch）：
   - 上游只 `target_link_libraries(ayatana-common ${DEPS_LIBRARIES})`，
     pkg_check_modules 只把 `-l` 放进 DEPS_LIBRARIES，`-L` 目录在
     DEPS_LIBRARY_DIRS 中；glib 为静态库（libglib-2.0.a）时缺 `-L` 导致
     CI `ld.lld: unable to find library -lglib-2.0/-lgio-2.0/-lintl/...`
   - 修复：`target_link_directories(ayatana-common PRIVATE ${DEPS_LIBRARY_DIRS})`
   - 与 jshn/foma/goocanvas 等包同法（显式补 LIBRARY_DIRS）

5. **shared 默认值**（conanfile.py `default_options = {"shared": True}`）：
   - 上游硬编码 SHARED，产物必然是共享库（非系统同名库，允许动态）
   - shared=True 让 conanrun 环境注入包 lib 目录，否则 test_package
     运行时找不到 libayatana-common.so

6. **test_package**：test() 用 `self.run(test_bin, env="conanrun")` 直接运行
   二进制（与 libx11/glib 同法）——ctest 不注入 conanrun 环境，SONAME 场景下
   运行时找不到库

## 产物
- lib/libayatana-common.so（带 DT_SONAME=libayatana-common.so）
- include/ayatana/common/utils.h
- lib/pkgconfig/libayatana-common.pc
- 库名（cpp_info.libs）: ayatana-common
---

**编译结束**: 2026-08-27 13:25
**最终状态**: published
