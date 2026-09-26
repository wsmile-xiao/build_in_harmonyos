# 老旧 CMake 2.x 项目同时构建 shared+static 同名库且依赖 pkg-config 的适配模式

- **草稿 ID**: DRAFT-libwebcam-0.2.5-legacy-cmake-shared-static-pkgconfig-inject
- **来源**: libwebcam 0.2.5 HarmonyOS PC 适配（CMake 2.6 + 同名 shared/static + pkg_check_modules 替换）
- **分类**: cmake / conan / legacy-build / pkg-config / ohos
- **状态**: 本地草稿（路径 B 知识库扩展）

## 问题 / 错误签名

1. **CMake 4.x 拒绝旧项目**：`cmake_minimum_required(VERSION 2.6)` 在 CMake 4.x 下报错
   `Compatibility with CMake < 3.10 will be removed`，部分项目直接配置失败。
2. **pkg_check_modules 在 headless OHOS 失败**：`pkg_check_modules(LIBXML2 REQUIRED libxml-2.0)`
   找不到 pkg-config 或 .pc 文件，配置阶段 FATAL_ERROR。
3. **同时构建 shared+static 同名目标**：上游 `add_library(webcam SHARED ...)` +
   `add_library(webcam_static STATIC ...)`，两者 `OUTPUT_NAME "webcam"`，Conan 的
   `shared=True/False` 选项无法控制。
4. **补丁文件未导出到 recipe cache**：`apply_conandata_patches()` 报
   `FileNotFoundError: patches/xxx.patch`，尽管 patches/ 目录存在于配方中。
5. **绝对路径 install 失败**：`install(DESTINATION /lib/udev/rules.d)` 在非 root 环境
   报 `file cannot create directory: /lib/udev/rules.d`。

## 根因

1. **CMake 策略版本**：CMake 3.5+ 移除了对 `cmake_minimum_required < 2.8.12` 的完整兼容，
   需要设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 让旧项目在新版 CMake 下工作。

2. **pkg-config 在 OHOS 不可靠**：headless 构建环境没有 pkg-config，也没有系统 .pc 文件。
   上游 `pkg_check_modules` 硬编码查找系统路径下的依赖。Conan 的 CMakeDeps 生成器对旧项目
   不自动生效（因为项目不 `find_package`），需要手动注入 `XXX_INCLUDE_DIRS` 和
   `XXX_LIBRARIES` 缓存变量。

3. **shared/static 无条件构建**：上游 CMakeLists 同时构建两个 target，Conan 的
   `BUILD_SHARED_LIBS` 变量不会自动切换。需要打补丁将 `add_library` 改为条件分支。

4. **补丁导出遗漏**：Conan 2.x 中，`apply_conandata_patches` 查找补丁文件时从
   source 目录搜索，而非 recipe 目录。必须：
   - 类属性声明 `exports_sources = "patches/*"`
   - `export_sources()` 方法中调用 `export_conandata_patches(self)`
   否则补丁文件不会从 recipe 导出到构建目录。

5. **绝对路径 install**：上游将 udev 规则安装到 `/lib/udev/rules.d`（绝对路径），
   Conan package 阶段没有 root 权限创建系统目录。

## 最小修复方案

在 `archives/<首字母>/<库名>/<版本>/` 范围内：

### 1. conanfile.py

```python
exports_sources = "patches/*"

def export_sources(self):
    export_conandata_patches(self)

def generate(self):
    tc = CMakeToolchain(self)
    # 旧 cmake_minimum_required 兼容 CMake 4.x
    tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
    # 注入依赖路径，绕过 pkg-config
    dep = self.dependencies["<dep>"]
    tc.cache_variables["<DEP>_INCLUDE_DIRS"] = os.path.join(
        dep.package_folder, dep.cpp_info.includedirs[0])
    dep_lib = "lib<dep>.so" if dep.options.shared else "lib<dep>.a"
    tc.cache_variables["<DEP>_LIBRARIES"] = os.path.join(
        dep.package_folder, dep.cpp_info.libdirs[0], dep_lib)
    tc.generate()
```

### 2. patches/0001-legacy-cmake.patch

```cmake
# 替换 pkg_check_modules
-#include (FindPkgConfig)
-pkg_check_modules (LIBXML2 REQUIRED libxml-2.0)
+if(NOT LIBXML2_INCLUDE_DIRS OR NOT LIBXML2_LIBRARIES)
+    message(FATAL_ERROR "LIBXML2 vars not injected by Conan")
+endif()

# 条件化 shared/static
-add_library (webcam SHARED libwebcam.c dynctrl.c)
-add_library (webcam_static STATIC libwebcam.c dynctrl.c)
+if(BUILD_SHARED_LIBS)
+add_library (webcam SHARED libwebcam.c dynctrl.c)
+else()
+add_library (webcam STATIC libwebcam.c dynctrl.c)
+endif()
```

### 3. 移除绝对路径 install

补丁中删除 `install(DESTINATION /lib/...)` 块，或在 `package()` 中清理。

## 实际验证结果

- **设备**: HarmonyOS PC aarch64 (ohos-aarch64-fixed profile)
- **编译**: `libwebcam.so` + `uvcdynctrl` 链接成功，exit=0
- **test_package**: C API smoke test 3/3 通过（c_get_error_text 错误字符串表）
- **上游测试通过率**: 0/N = N/A（上游无自动化测试框架，libwebcam/test.c 需物理 UVC 摄像头）
- **补丁应用**: 2 个 patch 干净应用（0001 cmake-compat + 0002 uvcdynctrl-ohos）

## 适用范围

- CMake 2.x/3.0 时代的老旧 C 库（2006-2012 年活跃项目）
- 使用 `pkg_check_modules` 而非 `find_package` 的项目
- 同时构建 shared 和 static 且 OUTPUT_NAME 相同的项目
- 在 headless OHOS 构建环境中没有 pkg-config 的场景

## 非适用边界

- 现代 CMake（>=3.10）项目：已有 proper `find_package` 和 target-based 构建，不需要此模式
- Meson/autotools 项目：有各自的依赖注入方式
- 已有 CMakeDeps 正确集成的项目

## 查重差异

- 与 E092（CMake 平台识别）不同：本条目不涉及 Platform/HarmonyOS 缺失，而是旧 CMake 项目
  在 Conan 2.x + CMake 4.x 下的构建系统适配
- 与 E093（pkg-config 不可用）主题相关，但本条目补充了：
  - shared/static 同名 target 的条件化补丁模式
  - `exports_sources` + `export_conandata_patches` 的完整导出链
  - 从 CMakeLists 分析到补丁到配方的端到端可复用流程

## 关联交付

- 本草稿与 `archives/l/libwebcam/0.2.5/**` 属于同一交付
- 随 PR 合并后进入主仓库知识库
- 正式 E 编号由知识库主编审核后分配

## 禁止模式

1. **手动设置 CMAKE_SYSTEM_NAME=Linux**：
   ```python
   # ❌ 不要这样做
   tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
   ```
   OHOS Conan toolchain 自动处理平台映射，手动覆盖可能导致加载错误的平台模块。

2. **不声明 exports_sources**：
   ```python
   # ❌ 补丁文件存在但不会被导出
   # 缺少 exports_sources = "patches/*"
   ```

## 推荐模式

```python
# ✅ 正确：完整的旧 CMake 项目适配
exports_sources = "patches/*"

def export_sources(self):
    export_conandata_patches(self)

def generate(self):
    tc = CMakeToolchain(self)
    tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
    dep = self.dependencies["<dep>"]
    tc.cache_variables["<DEP>_INCLUDE_DIRS"] = os.path.join(
        dep.package_folder, dep.cpp_info.includedirs[0])
    tc.generate()
```

## 关联原则

- P010：尊重上游构建逻辑，用 Conan 工具链注入而非重写
- P020：消费者测试必须验证真实 API 调用

## 相似条目

- E092：CMake 平台识别
- E093：pkg-config 不可用替代方案
