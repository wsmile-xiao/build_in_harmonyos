# libkexiv2 26.04.0 适配笔记

## 编译环境
- 构建系统: cmake（KDE Gear release-service 源码包，上游 project version 5.1.0）
- 编译日期: 2026-09-14
- 编译器: clang 15.0.4（由 Conan profile `ci/conan/profiles/ohos-aarch64` 的 `tools.build:compiler_executables` 提供，配方未硬编码编译器路径）
- 目标平台: OpenHarmony / HarmonyOS PC aarch64（`os=OHOS`, `arch=armv8`）
- 状态: built

## 编译步骤

```bash
# 1) 依赖已发布验证（W0/R36，二进制层）
conan install --requires=qtbase/6.11.1 --requires=exiv2/0.28.7 \
    --tool-requires=ecm/6.26.0 --build=never \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 2) 语言预检（R47）
python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight libkexiv2 26.04.0 --src <src>

# 3) 构建 + 上游测试入口执行 + test_package
conan create archives/l/libkexiv2/26.04.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方关键点（**无源码补丁**）：

| 项 | 处理 |
|---|---|
| 依赖解析 | 不使用 CMakeDeps：qtbase 为 `cmake_find_mode=none`（自带完整 Qt6Config.cmake），exiv2 走包内上游 `exiv2Config.cmake`（正是它定义了项目要链接的 `Exiv2::exiv2lib`）。`conan_cmakedeps_paths.cmake` 手工声明**全部 host 依赖**（qtbase/exiv2 及传递的 expat/zlib）的 `lib/cmake`、`lib`、`include` 路径（libkcddb 26.04.3 / kfilemetadata 6.28.0 先例） |
| `CMAKE_FIND_PACKAGE_PREFER_CONFIG` | **刻意不设置**（原因见问题 #5） |
| `ECM_MODULE_PATH` | 无需手工注入：消费 ecm 自带的 `ECMConfig.cmake` 已设置该变量 |
| SONAME | 补齐 `KEXIV2_VERSION`/`KEXIV2_SOVERSION` + 注入 `-Wl,-soname,` 标志 + `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`（原因见问题 #2） |
| OHOS 加载器软链接限制 | 依赖的 soname 别名**复制**实体化到私有 `runtime-libs/`（原因见问题 #1） |
| 上游测试 | `BUILD_TESTING=ON` 编译 tests/ 下 7 个演示程序，`build()` 中逐个真实执行 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 阶段 `qtpaths` 报 `Error loading shared library libQt6Core.so.6`；上游演示程序运行期同类报错 | HarmonyOS 加载器**不能通过软链接加载共享库**。自研小库对照实验：`libfoo.so.1 -> libfoo.so.1.0.0` 软链接退出码 127，同字节**副本**退出码 0；`/storage` 与 `/data/storage/el2/base/temp` 两处文件系统结果一致。⇒ qtbase 包内 `libQt6Core.so.6 -> libQt6Core.so.6.11.1` 链不可加载（E018/E511） | 配方把依赖 soname 别名（`libQt6Core.so.6`、`libQt6Gui.so.6`、`libexpat.so.1`）**复制**到私有 `<build>/runtime-libs/` 并前置 `LD_LIBRARY_PATH`（E511 rec_approach=materialize-versioned-so-aliases）；`test_package` 同样处理 |
| 2 | 产物无 `DT_SONAME`，会被 CI **L5a 门禁**判失败（`[fail] L5a: ... 缺少 DT_SONAME`） | ① CMake 无 `Platform/HarmonyOS` 模块，`CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` 为空 → 链接器收不到 `-soname`；② 本环境 ECM/CMake 组合下 `ecm_setup_version()` 未把 `KEXIV2_VERSION`/`KEXIV2_SOVERSION` 回传到调用作用域（版本头文件里 `KEXIV2_VERSION_STRING` 却正常为 5.1.0），src/CMakeLists 的 `set_target_properties(... VERSION/SOVERSION ...)` 拿到空值 | 配方在 toolchain（先于 project 加载，src/ 可见）中补齐 `KEXIV2_VERSION=5.1.0`、`KEXIV2_SOVERSION=0`；注入 `CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG=-Wl,-soname,`；并置 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`（Android 平台先例）使 SONAME 保持**不版本化** → 产物为单个 `libKExiv2Qt6.so`（带 SONAME，无软链接链，恰好绕开 #1 的加载器限制） |
| 3 | 演示程序退出码 127（修完 #1/#2 后仍出现一次） | 带 SONAME 后工具 DT_NEEDED 变为纯名 `libKExiv2Qt6.so`，而工具**无 RPATH**，库又在 KDE 单目录布局的 `<build>/bin` | `_runtime_env()` 把 `<build>/bin`、`<build>/lib` 一并前置到 `LD_LIBRARY_PATH`（libkcddb 先例） |
| 4 | configure 报 `Could NOT find ZLIB (missing: ZLIB_LIBRARY ZLIB_INCLUDE_DIR)` | `exiv2Config.cmake` 的 `find_dependency(ZLIB/EXPAT)` 走 CMake 模块模式，需要头/库目录在搜索路径上；只加直接依赖（qtbase/exiv2）不够 | `conan_cmakedeps_paths.cmake` 遍历**全部 host 依赖**注入 `CMAKE_PREFIX_PATH`/`CMAKE_LIBRARY_PATH`/`CMAKE_INCLUDE_PATH` |
| 5 | generate 阶段：`The link interface of target "Exiv2::exiv2lib" contains: EXPAT::EXPAT but the target was not found` | exiv2 静态闭包写作 `$<LINK_ONLY:EXPAT::EXPAT>`；若 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`，嵌套 `find_dependency(EXPAT)` 会命中 conan 的 `expat-config.cmake`（只导出 `expat::expat`），模块模式 `FindEXPAT`（才会创建 `EXPAT::EXPAT`）被跳过 | **不设置** `CMAKE_FIND_PACKAGE_PREFER_CONFIG`，让 `find_dependency(EXPAT)` 走模块模式 |
| 6 | `setxmpface` 退出码 255 | 该工具真实接口是 `<add\|remove> <image>` 两个参数（`argc != 3` 即打印用法并返回 -1） | 按各工具真实接口传参：`setxmpface add <image>`；`printtagslist` 不传参；其余 6 个传 `<image>` |
| 7 | `init-build` 首次把归档建到 SKILL 自带克隆目录 | `find_project_dir()` 优先返回脚本所在项目（SKILL 资源目录内也是一份完整克隆） | 调用前显式 `export OHC_PROJECT_DIR=/storage/Users/currentUser/runner_AVA/build_in_harmonyos`，并清理误建产物 |

## 源码修改

无。未生成任何补丁（`patches: {}`），源码保持上游 release-service 26.04.0 原样。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| qtbase | 6.11.1 | 项目要求 Qt6 >= 6.5.0（Core/Gui） |
| exiv2 | 0.28.7 | 项目要求 exiv2 >= 0.27；conan 包为静态库（libexiv2.a），链接进 libKExiv2Qt6.so |
| ecm | 6.26.0 | 构建工具（tool_requires），项目要求 ECM >= 6.0 |
| zlib | 1.3.1.1 | exiv2 传递依赖（静态） |
| expat | 2.8.2.1 | exiv2 传递依赖（共享库，运行期需实体化 libexpat.so.1） |

## 上游测试申报表（R51）

| 项 | 实测值 |
|---|---|
| 上游测试目录 | `tests/` 1 个，含 7 个源文件 + `CMakeLists.txt` |
| 自动化用例注册数（ctest） | **0**（`ctest --test-dir <build> -N` → `Total Tests: 0`；全树无 `add_test()`、无 `enable_testing()`、无断言框架） |
| 是否有测试夹具 | 无（上游不含任何图片样例） |
| 真实测试入口 | tests/ 下 7 个演示程序（`add_executable`）；`BUILD_TESTING=ON` 编译 |
| 实跑结果 | **7/7 退出码 0**（erasetag、loadfromba、printtagslist、readimagewritexmpsidecar、setiptcpreview、setxmpface add、usexmpsidecar） |
| 夹具来源 | 配方内嵌 8x8 JPEG（629 B，Qt6 生成），build() 写入 `<build>/upstream-sample.jpg` |
| 日志 | `reports/upstream-tests.log`、`reports/upstream_test_result.json` |

有意义的输出证据：`printtagslist` 打印完整 Exiv2 标签注册表（Std Exif + Makernote + XMP）；`setxmpface add` 输出 `Image support XMP true` 与 `Saved name is: "Bob Marley"`（XMP 结构化写入+回读成功）；`erasetag` 输出 `Exif.OlympusIp.BlackLevel found = false / removed = true`。

## 验证结果

```bash
# 上游测试入口（ctest 注册 0 + 7 个演示程序实跑）
ctest --test-dir <build_folder> -N                       # Total Tests: 0
<build_folder>/bin/{erasetag,loadfromba,printtagslist,readimagewritexmpsidecar,
                    setiptcpreview,setxmpface add,usexmpsidecar} <sample.jpg>
# 7/7 exit_code=0

# 消费者测试（test_package）
conan create archives/l/libkexiv2/26.04.0 -pr:h=... -pr:b=...
# checks=24 failures=0
#   libkexiv2 version: 5.1.0 / libexiv2 version: 0.28.7
#   EXIF / 日期时间 / XMP 写入-回读往返全部 ok

# 产物 SONAME（CI L5a）
readelf -d <package>/lib/libKExiv2Qt6.so | grep SONAME
#   (SONAME) Library soname: [libKExiv2Qt6.so]
```

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | Conan 配方（无 CMakeDeps；依赖 soname 别名实体化；SONAME 修复；上游演示程序执行） |
| `conandata.yml` | 官方源码 URL + sha256（`patches: {}`） |
| `test_package/` | conanfile.py + CMakeLists.txt + test_package.cpp + MANIFEST.yml（24 项断言） |
| `reports/upstream-tests.log` | 上游测试入口完整日志（截断标签转储） |
| `reports/upstream_test_result.json` | 7 个演示程序逐项退出码 |

## 注意事项

1. **不要恢复 `CMAKE_FIND_PACKAGE_PREFER_CONFIG ON`**，否则 exiv2 的 `EXPAT::EXPAT` 闭包解析失败，configure 会在 generate 阶段报错（问题 #5）。
2. **不要去掉 `CMAKE_PLATFORM_NO_VERSIONED_SONAME`**：一旦 CMake 生成版本化软链接链，OHOS 加载器无法加载（问题 #1），且下游 DT_NEEDED 会记录不可重定位路径。
3. 上游 7 个演示程序**不是自动化测试**（无断言、无 ctest 注册），PR 中不得把它们统计为"上游测试用例通过率"；其价值是端到端跑通了 EXIF/IPTC/XMP 读写路径。
4. 本环境下 `ecm_setup_version()` 未把 `KEXIV2_VERSION`/`KEXIV2_SOVERSION` 回传调用作用域（版本头正常、target 属性为空），配方以 toolchain 变量补齐；若上游/ECM 修复该行为，配方中的两个变量与上游值一致、无副作用。
---

**编译结束**: 2026-09-14 03:23
**最终状态**: built
