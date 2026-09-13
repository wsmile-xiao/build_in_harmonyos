# ayatana-indicator-display 26.6.0 — 适配笔记

## 上游信息
- 仓库: https://github.com/AyatanaIndicators/ayatana-indicator-display
- 版本: 26.6.0（2026-06-13 发布，tag: 26.6.0）
- 源码: `archive/refs/tags/26.6.0.tar.gz`，sha256=`57f0dfd3b47416cb4ad5b66baec2ad57ad59aa604f1e10f5b584f64fdbcbdffc`
- 构建系统: CMake（min 3.13，C/C++）

## 功能定位
显示菜单系统指示器服务：亮度（brightness）控制、可选色温（colour temperature）。
产物：`libayatana-indicator-display.a`（STATIC）+ `ayatana-indicator-display-service`
可执行（安装到 `libexec/ayatana-indicator-display/`）。

## OHOS 适配要点
1. **依赖**（顶层 CMakeLists `pkg_check_modules(SERVICE_DEPS REQUIRED ...)`）：
   - `libayatana-common >= 0.9.3`（制品仓 0.9.13）
   - `gio-unix-2.0` / `glib-2.0`（制品仓 glib/2.88.0.1）
   - `properties-cpp >= 0.0.1`（制品仓 0.0.4，header-only）
   - 通过 PkgConfigDeps 生成 .pc（CMakeToolchain 自动注入 PKG_CONFIG_PATH）
2. **SKIP_DATA_PO=ON**（0001 补丁）：
   - `data/CMakeLists.txt` 用 `find_package(GSettings REQUIRED)` + `add_schema`
   - `po/CMakeLists.txt` 用 `find_package(Intltool REQUIRED)`
   - OHOS 均无这些 CMake 模块 → 跳过 data/ 与 po/ 子目录（与 libayatana-common 同法）
3. **ENABLE_COLOR_TEMP=OFF / ENABLE_RDA=OFF**：
   - 默认 ON 时 `SERVICE_DEPS` 追加 `libgeoclue-2.0 accountsservice x11 xrandr [rda]`
   - OHOS 无这些桌面库；关闭后 service.cpp 色温分支不编译，亮度控制不受影响
4. **ENABLE_TESTS=OFF**：上游 tests/ 依赖 Qt5Test/Qt5DBus/libqtdbtest-1/
   libqtdbusmock-1/GMock + cppcheck，OHOS 制品仓无 Qt5/qtdbtest/qtdbusmock

## 上游测试（真实统计）
- `tests/unit/rotation-lock-test.cpp`：**1 个 TEST_F（RotationLockFixture.CheckIndicator）**，
  含 8 个断言（indicator.name()=display、action_group 非空且含 rotation-lock、
  profiles 2 个 phone/desktop、header->is_visible 断言）。
  依赖 Qt5Test/Qt5DBus/libqtdbtest-1/libqtdbusmock-1/GMock（tests/CMakeLists.txt
  find_package(GMock/Qt5Test/Qt5DBus) REQUIRED + pkg_check_modules TEST_DEPS
  libqtdbtest-1/libqtdbusmock-1）——制品仓无 Qt5/qtdbtest/qtdbusmock，
  **OHOS 不可运行**（ENABLE_TESTS=OFF，如实不虚报）。
- `tests/CMakeLists.txt`：cppcheck 静态分析（`--enable=all --error-exitcode=2`），
  OHOS 无 cppcheck 工具链，未运行。
- 适配后 test_package 端到端验证（1 项）：service 可执行文件存在 +
  conanrun 环境启动（deps linked），对应上游"库可被消费"验证维度。

## 产物
- `libexec/ayatana-indicator-display/ayatana-indicator-display-service`（可执行）
- 运行时依赖：libayatana-common.so、glib/gio、libc++_shared.so（经 conanrun 注入）
