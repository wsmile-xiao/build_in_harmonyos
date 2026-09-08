# libayatana-common 0.9.11 适配笔记

## 编译环境
- **构建系统**: CMake
- **编译日期**: 2026-09-03
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0

## 编译步骤（conan create 全流程）

```bash
conan create archives/l/libayatana-common/0.9.11 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 GitHub gh-proxy tarball 下载（0.9.11 tag）。

### 2. 依赖注入（generate()）
- glib/2.84.0（glib-2.0 ≥ 2.36 / gio-2.0 ≥ 2.36）——ohpcd 已发布
- 复制**所有依赖包**（含 glib 的 Requires 链传递依赖 pcre2/libffi 等）pkgconfig
  目录的 .pc 到 generators_folder 并改写 prefix/libdir，保证 CMake 的
  pkg_check_modules(DEPS glib-2.0/gio-2.0) 可解析
- build() 里把各依赖 pkgconfig 目录注入 os.environ PKG_CONFIG_PATH

### 3. 构建（build()）
- CMake configure + build
- 关闭可选特性：ENABLE_TESTS/ENABLE_WERROR/ENABLE_COVERAGE/ENABLE_LOMIRI_FEATURES
  均 OFF（OHOS 无 Lomiri 运行时、无 gobject-introspection 工具链）
- 上游测试：ENABLE_TESTS 默认 OFF；ctest 尝试执行并记录结果（rule 1.2 平台限制）

### 4. 打包（package()）
- cmake install；产物：libayatana-common.so（C/C++ 公共基础设施库）+ 头文件

## 依赖
- glib/2.84.0（ohpcd 已发布）

## 上游测试（rule 4 整改）
- tests/ 下 tst_utils.cpp gtest 注册 **9 个用例**（TEST_F 宏：isLomiri/
  isUbuntuTouch/isGnome/isUnity/isMate/isXfce/isPantheon/isBudgie + ellipsize，
  注册 2 个 CTest 项：TstUtils + TstUtilsVala，与评审口径一致）；
  另有 tst_utils.vala（Vala 用例，需 valac）
- **rule 4 整改**：此前归因「OHOS 无 gtest 运行环境」不充分——gtest 为
  header-only 框架，OHOS 可实跑。已开启 ENABLE_TESTS=ON + gtest/gmock 依赖
  （requirements），并新增 0003（tst_utils_vala 的 "src" target 引用 →
  "ayatana-common"）+ 0004（gschemas.compiled schema 依赖路径从构建目录改为
  源码目录）两个构建修复补丁
- **实测运行**：OHOS 实跑上游 gtest 套件 **9/9 = 100% 通过**（8/8
  XdgCurrentDesktopUtilsTest + 1/1 StringFunctionsTest.ellipsize）——
  日志见 PR 描述「上游 gtest 实测运行日志」；ellipsize 用例需 GSETTINGS_SCHEMA_DIR
  指向 gschemas.compiled（glib-compile-schemas 编译 org.ayatana.common.gschema.xml）
- 本地验证：conan create 通过，libayatana-common 库与头文件编译链接成功
- 适配后：test_package R34 真实产物校验——libayatana-common.so 存在 + ELF
  shared object，1/1 = 100%

## 已知限制
- Ayatana 指示器框架在 OHOS 无运行环境（Lomiri 会话/桌面子系统）——API 可编译
  打包，运行类功能按平台限制声明
