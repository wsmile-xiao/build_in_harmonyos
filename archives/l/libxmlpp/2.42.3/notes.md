# libxmlpp 2.42.3 适配笔记（synfig 依赖项）

## 编译环境
- 构建系统: Meson
- 编译日期: 2026-08-02
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18, aarch64-linux-ohos)
- 平台: HarmonyOS PC aarch64, musl libc
- 状态: built（本地验证通过，尚未 CI upload；CI 成功后更新为 published）

## 角色
作为 **synfig 1.5.5 的依赖项**：synfig-core/src/CMakeLists.txt 探测
`pkg_check_modules(XMLPP REQUIRED IMPORTED_TARGET libxml++-2.6)`，需要
libxml++-2.6.pc。由 CI 从源码构建，不依赖制品仓预发布。

## 版本裁决（关键，勿回退）
- synfig 1.5.5 探测 pc 名 **libxml++-2.6**，只与 2.x 旧 API 线兼容
- 2.x 线官方最新为 **2.42.3**（2024-01-11 发布，GNOME 目录 LATEST-IS-2.42.3；**不存在 2.46 线**）
- 5.x（pc libxml++-5.0）是 NEW-API 线，不满足 synfig
- 故选用 libxml++ **2.42.3**（2.x 线官方最新）

## 依赖关系
- **glibmm/2.66.9**（2.x 线专用依赖）：libxml++ 2.x 基于 glibmm-2.4
  （Glib::ustring / Glib::RefPtr），meson 探测 `dependency('glibmm-2.4', '>= 2.32.0')`
- **libxml2**：cmd-pkgs 系统包（系统 libxml-2.0.pc，共享库）。
  本环境只有共享 libxml2.so（无静态 libxml2.a，E076 静态化前提不成立），经系统 pc 解析。

## 编译步骤
1. 下载 GNOME 官方 release tarball（download.gnome.org/sources/libxml++/2.42/）
2. conanfile.build(): MesonToolchain + Meson
3. 产物: libxml++-2.6.a/.so + libxml++-2.6.pc

## 验证结果
- conan-verify: G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS
- test_package: 头文件包含 + 链接 + 原生运行（libxml++ 2.x API 冒烟）
- 人工门禁补充: reports/manual-gates-supplement.md

## 遗留说明
- libxml2 为共享库系统依赖；若未来需要静态链 libxml2.a（E076 方案），
  需先通过 cmd-pkgs 补齐静态包
