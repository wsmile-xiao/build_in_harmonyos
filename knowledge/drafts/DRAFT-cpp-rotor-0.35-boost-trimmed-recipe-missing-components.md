# DRAFT — cpp-rotor 0.35：制品仓 Boost 裁剪版配方缺失组件/头文件时选用完整配方版本

## 问题（Problem）

在 HarmonyOS PC（aarch64/OHOS，Conan 2）适配依赖 Boost 的 C++ 库（如 cpp-rotor 0.35，
其 CMakeLists 链接 `Boost::date_time Boost::system Boost::regex` 并包含
`boost/lockfree/queue.hpp`、`boost/date_time/posix_time/posix_time.hpp`）时，使用制品仓
`ohpcd` 中部分 Boost 版本会同时出现两类失败：

1. **CMakeDeps 配置期**：`CMake Error at CMakeLists.txt (target_link_libraries): Target "rotor"
   links to: Boost::date_time but the target was not found` —— 裁剪版配方未声明
   `date_time` 组件，CMakeDeps 未生成 `Boost::date_time` 目标；
2. **编译期**：`fatal error: 'boost/lockfree/queue.hpp' file not found` —— 裁剪版配方按
   组件导出头文件，header-only 的 `lockfree` 不在组件列表，头文件未打包。

## 根因（Root Cause）

制品仓 Boost 配方存在两类：

- **裁剪版**（如 `boost/1.90.0.4`、`boost/1.91.0`、`boost/1.91.0.1`）：`_components` 仅列出
  编译的组件子集（如 atomic/chrono/filesystem/program_options/regex/serialization/system/
  thread/timer），缺 `date_time`；且头文件按组件裁剪导出，`include/boost/lockfree/`、
  `include/boost/posix_time/` 等 header-only 路径不存在。CMakeDeps 生成的
  `Boost-Target-release.cmake` 只有声明的组件目标，导致下游 `find_package(Boost ...)` 或
  `target_link_libraries(Boost::xxx)` 失败；
- **完整版**（如 `boost/1.84.0`、`boost/1.90.0`）：标准 conan-center 风格配方，`package_info()`
  导出全部组件（`boost_date_time`/`boost_system`/`boost_regex` 等，`cmake_target_name` 为
  `Boost::date_time` 等），头文件完整包含 `lockfree`、`date_time` 路径。

## 方案（Solution）

在 `conanfile.py` 的 `requirements()` 中选用制品仓**完整配方**版本（本项目使用
`boost/1.84.0`），并：

- `self.requires("boost/1.84.0", transitive_headers=True)`；
- `generate()` 同时生成 `CMakeDeps` + `CMakeToolchain`（`tc.variables["BUILD_SHARED_LIBS"]`
  按 `shared` 选项设置，关闭上游 tests/examples/asio/ev/wx/fltk 等可选组件）；
- `package_info()` 中 `self.cpp_info.requires` 使用 **conan 组件名**而非 CMake 目标名：
  `["boost::boost_date_time", "boost::boost_system", "boost::boost_regex"]`
  （写成 `boost::date_time` 会在 test_package 的 CMakeDeps 生成期报
  `Component 'boost::date_time' not found in 'boost' package requirement`）；
- 注意：Boost.System 自 1.69 起为 header-only，`libboost_system` 不存在属正常现象。

## 验证（Verification）

```bash
# 上游测试（Catch2 v2 兼容环境下）25/25 通过：
ctest --output-on-failure   # 100% tests passed, 0 failed out of 25

# conan-verify G0-G4 全 PASS；finish（含 W2/W3 conan create）exit 0
python3 scripts/ohc-run.py conan-verify cpp-rotor 0.35   # ✅ 配方验证通过，可标记 published
```

## 适用边界（Scope）

- 适用于依赖 Boost 多组件/header-only 头文件的 C++ 库在 OHOS aarch64 + Conan 2 的适配；
- 选择制品仓中存在的完整配方 Boost 版本（1.84.0 等）即可，无需手工补头文件或
  注入 missing target；
- 若制品仓只有裁剪版且下游必须使用某组件，才需要额外处理（补模块/注入目标）。

## 反例 / 限制（Counter-examples / Limitations）

- 裁剪版 Boost 用于仅依赖 `boost::boost`（header-only compat）的下游时可工作，无需换版本；
- `boost/1.90.0.4` 等裁剪版并非损坏，而是按需裁剪；选用哪个版本取决于下游所需组件集合。

## 查重差异（Dedup Difference）

知识图谱中无等价条目：E099/E153（boost b2 构建系统不兼容 OHOS）、E355（meson 平台映射 +
boost 裁剪模块手工补全）、E216（glib/libxml2 CMakeDeps 组件头文件传播失效）、E473
（libwebp 缺 WebP::webpdemux target 时注入 missing target）均与本条目的根因/方案不同。
