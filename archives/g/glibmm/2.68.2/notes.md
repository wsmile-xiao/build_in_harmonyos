# glibmm 2.68.2 适配笔记（目标库首轮）

## 编译环境
- 构建系统: Meson（tarball 为 meson dist 产物，自带 untracked/ 预生成绑定）
- 编译日期: 2026-08-17
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18, aarch64-linux-ohos)
- 平台: HarmonyOS PC aarch64, musl libc
- 状态: built（本地验证）

## 版本裁决（关键，勿回退）
- glibmm **2.68 是 glibmm-2.68 ABI 线**（glibmm-2.68.pc / giomm-2.68.pc，
  libglibmm-2.68.so / libgiomm-2.68.so），依赖 **sigc++-3.0（libsigc++ 3.x）**
- glibmm 2.66.x 是最后提供 glibmm-2.4.pc / libglibmm-2.4.so 的 2.4 ABI 线
  （sigc++-2.0 / libsigc 2.10.8）
- 故本配方固定 glibmm **2.68.2**（2.68 线官方最新，LATEST-IS-2.68.2）

## 依赖
- glib/2.84.0.1（glib-2.0 / gobject-2.0 / gmodule-2.0 / gio-2.0 / gio-unix-2.0，
  上游要求 >= 2.63.0）— 已发布 ohpcd
- libsigc/3.0.6（sigc++-3.0，上游要求 >= 3.0.0）— 已发布 ohpcd

## 编译步骤
1. 下载 GNOME 官方 release tarball（meson dist 产物，含 untracked/ 预生成绑定）
2. conanfile.build(): MesonToolchain + Meson，maintainer-mode=false（无需 mm-common/gmmproc）
3. 构建测试：meson test -C build --timeout-multiplier=16 --no-rebuild --no-suite=failing
4. 产物: libglibmm-2.68.a / libgiomm-2.68.a + glibmm-2.68.pc / giomm-2.68.pc

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | giomm_tls_client_test 失败 | OHOS 平台无法连接网络（E215） | 0001 补丁标记 failing suite，build() 用 --no-suite=failing 跳过 |

## 验证结果
- test_package: 头文件包含 + 链接 + 原生运行（ustring/compose/convert/DateTime/Gio::File/sigc++-3.0 集成）
- 上游测试: 33 runtime + 2 should_fail（35 项，按平台排除需说明）
