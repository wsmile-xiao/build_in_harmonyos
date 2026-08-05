# glibmm 2.66.9 适配笔记（synfig 依赖项）

## 编译环境
- 构建系统: Meson（tarball 为 meson dist 产物，自带 untracked/ 预生成绑定）
- 编译日期: 2026-08-02
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18, aarch64-linux-ohos)
- 平台: HarmonyOS PC aarch64, musl libc
- 状态: published（本地验证通过，作为 synfig 依赖项随 PR 提交）

## 角色
作为 **synfig 1.5.5 的依赖项**：synfig-core/src/CMakeLists.txt 探测
`pkg_check_modules(GLIBMM REQUIRED IMPORTED_TARGET glibmm-2.4)`，需要
glibmm-2.4.pc。由 CI 从源码构建，不依赖制品仓预发布。

## 版本裁决（关键，勿回退）
- libxml++ 2.42.3（libxml++-2.6.pc）meson 探测 `dependency('glibmm-2.4', version: '>= 2.32.0')`
- glibmm **2.66.x 是最后提供 glibmm-2.4.pc / libglibmm-2.4.so 的 2.4 ABI 线**
- glibmm 2.68+（含 2.84.0）改为 glibmm-2.68 ABI（sigc++-3.0），不满足 libxml++ 2.x
- 故固定 glibmm **2.66.9**（2.4 ABI 线官方最新）

## 编译步骤
1. 下载 GNOME 官方 release tarball（meson dist 产物，含 untracked/ 预生成绑定）
2. conanfile.build(): MesonToolchain + Meson，maintainer-mode=false（无需 mm-common/gmmproc）
3. 构建测试：meson test --timeout-multiplier=16 --no-rebuild --no-suite=failing
4. 产物: libglibmm-2.4.a / libgiomm-2.4.a + glibmm-2.4.pc / giomm-2.4.pc

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | giomm_tls_client_test 失败 | OHOS 平台无法连接网络（E215） | 0001 补丁标记 failing suite，build() 用 --no-suite=failing 跳过 |

## 验证结果
- conan-verify: G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS
- test_package: 头文件包含 + 链接 + 原生运行（ustring/compose/convert/DateTime/Gio::File/sigc 集成，9 断言）
