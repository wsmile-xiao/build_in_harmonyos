# DRAFT: GLib 测试框架在 conan PkgConfigDeps 下的 CMake 变量注入

- **草稿 ID**: `DRAFT-ohos-glib-test-framework-cmake-inject`
- **触发软件**: libayatana-common 0.9.11
- **状态**: DRAFT（待主编/AI 审核提升为 E 条目）
- **姊妹条目**: DRAFT-ohos-intltool-toolchain-stub（dbustest，intltool 工具链 stub——同属 GLib 测试框架适配链，问题层不同、互补）

## 问题

GLib 系库开启测试（`ENABLE_TESTS=ON`）时，`tests/CMakeLists.txt` 通常含三类
在 conan PkgConfigDeps 环境下不可靠的依赖：

### 1. gschemas.compiled 生成器（Error 126）

```cmake
# tests/CMakeLists.txt
execute_process(COMMAND ${PKG_CONFIG_EXECUTABLE} gio-2.0
                --variable glib_compile_schemas
                OUTPUT_VARIABLE COMPILE_SCHEMA_EXECUTABLE ...)
```

用 pkg-config 查 `glib-compile-schemas` 工具路径（编译 GSettings schema）。
OHOS conan 环境下该查询**不可靠**：

| 查询路径 | 结果 |
|---------|------|
| build() 注入的 PKG_CONFIG_PATH 指向 glib 原始 .pc（prefix=/ 未改写） | 返回 `//bin/glib-compile-schemas` 错误路径 |
| generators_folder 的 .pc（PkgConfigDeps 生成） | **不含 `glib_compile_schemas` 自定义变量** → 返回空 |

CMake 命令退化为 `./.` → `Error 126`（cannot execute）。

### 2. gtest/gmock 头与库路径（not found / undefined symbol）

```cmake
find_package(GMock)
target_link_libraries(tst_utils ... ${GTEST_LIBRARIES} ${GTEST_BOTH_LIBRARIES} ${GMOCK_LIBRARIES})
```

conan PkgConfigDeps 下 `find_package(GMock)` **不设置**这些变量（返回空）：
- include 缺路径 → `gtest/gtest.h file not found`
- 库缺路径 → `undefined symbol: testing::internal::MakeAndRegisterTestInfo`

### 3. gtest/gmock 依赖声明（package_info 报错）

```python
# conanfile.py requirements()
self.requires("gtest/1.17.0")   # ❌ 库本身不引用它们
self.requires("gmock/1.17.0")
```

仅测试编译用、非库运行时依赖——conan 报
`package_info(): direct dependency 'gmock' is not used by any (cpp_info/components).requires`。

## 方案（conanfile.py generate() 注入 + tests/CMakeLists.txt 补丁）

### 1. COMPILE_SCHEMA_EXECUTABLE 注入

```python
# conanfile.py generate()
glib_pkg = self.dependencies["glib"].package_folder
tc.variables["COMPILE_SCHEMA_EXECUTABLE"] = os.path.join(glib_pkg, "bin", "glib-compile-schemas")
```

```cmake
# tests/CMakeLists.txt 补丁：仅当未注入时才 pkg-config 查询
if(NOT DEFINED COMPILE_SCHEMA_EXECUTABLE)
  execute_process(COMMAND ${PKG_CONFIG_EXECUTABLE} gio-2.0 --variable glib_compile_schemas OUTPUT_VARIABLE COMPILE_SCHEMA_EXECUTABLE OUTPUT_STRIP_TRAILING_WHITESPACE)
endif()
```

### 2. gtest/gmock 头与库绝对路径注入

```python
# conanfile.py generate()
tc.variables["GTEST_INCLUDE_DIR"]   = os.path.join(gtest_pkg, "include")
tc.variables["GMOCK_INCLUDE_DIR"]   = os.path.join(gmock_pkg, "include")
tc.variables["GTEST_LIBRARIES"]     = os.path.join(gtest_pkg, "lib", "libgtest.a")
tc.variables["GTEST_BOTH_LIBRARIES"] = ";".join([gtest_main.a, gtest.a])
tc.variables["GMOCK_LIBRARIES"]     = os.path.join(gmock_pkg, "lib", "libgmock.a")
```

```cmake
# tests/CMakeLists.txt 补丁
target_include_directories(tst_utils PUBLIC "${CMAKE_SOURCE_DIR}/src"
    "${DEPS_INCLUDE_DIRS}" "${GTEST_INCLUDE_DIR}" "${GMOCK_INCLUDE_DIR}")
target_link_directories(tst_utils PUBLIC ${DEPS_LIBRARY_DIRS})
target_link_libraries(tst_utils ... ${GMOCK_LIBRARIES} ${GLIB_INTL_LIBRARY})
```

> `DEPS_INCLUDE_DIRS`/`DEPS_LIBRARY_DIRS` 由 `pkg_check_modules(DEPS glib-2.0 gio-2.0)` 提供（含 glib 头/库路径）；`target_link_directories` 缺省会报 ld 找不到 `-lglib-2.0` 等。

### 3. gtest/gmock 改 test_requires

```python
# conanfile.py —— requirements() 移出，build_requirements() 加入
def build_requirements(self):
    self.test_requires("gtest/1.17.0")
    self.test_requires("gmock/1.17.0")
```

仅测试编译运行用，非库运行时依赖——避免 package_info 的 direct dependency 报错。

## 验证

libayatana-common 0.9.11：conan-verify 全门禁 PASS（G0-G5/L2/L4/L5），
gtest 实测 **9/9=100%**（tst_utils.cpp 手动编译运行 + SCHEMA_DIR 重编译）；
gschemas.compiled 正常生成、gtest 编译链接成功、package_info 无 gmock 依赖声明报错。

## 推广价值

适用于所有 GLib 系库（ENABLE_TESTS=ON + GSettings schema + gtest/gmock 测试）
在 conan PkgConfigDeps 环境的适配——ayatana/gnome 组件普遍适用。与
DRAFT-ohos-intltool-toolchain-stub 同属 GLib 测试框架适配链。

## 相关条目

- DRAFT-ohos-intltool-toolchain-stub：intltool 工具链 stub（GLib 测试框架适配链，检查层）
- E499：conan shared-package 传递运行时 libdirs
- DRAFT-conan-shared-pkgconfig-requires-drop
