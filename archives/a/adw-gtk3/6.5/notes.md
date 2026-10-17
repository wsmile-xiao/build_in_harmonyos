# adw-gtk3 6.5 适配笔记

## 基本信息
- **软件名称**：adw-gtk3（The theme from libadwaita ported to GTK-3）
- **版本**：6.5（上游 tag v6.5，2026-04-13 发布，面向 GNOME 50）
- **许可证**：LGPL-2.1
- **上游仓库**：https://github.com/lassekongo83/adw-gtk3
- **类型**：GTK3/GTK4 主题数据包（SCSS 源由上游 CI 用 sass 编译为 CSS）

## 三重身份映射
- 平台身份：adw-gtk3 / 6.5 / Issue #2002 / 分支 feat/adw-gtk3-6.5
- 上游身份：lassekongo83/adw-gtk3 / tag v6.5 / GitHub / LGPL-2.1
- 归档身份：Conan adw-gtk3/6.5 / archives/a/adw-gtk3/6.5
- 三组名称与版本一致，无歧义。

## 源码与校验
- **源码 URL**：https://github.com/lassekongo83/adw-gtk3/releases/download/v6.5/adw-gtk3v6.5.tar.xz
- **SHA256**：a81780fadfc432be0fc3d89c4ebb41aa28e4f032d42c36f9789c57dd10cfa41c
- 已实际下载并核验：xz 压缩数据，121,632 字节；解压后为 adw-gtk3/ 与 adw-gtk3-dark/
  两个主题目录（各含 gtk-3.0/、gtk-4.0/、index.theme），共 134 个文件。
- 与源码 tag 归档（fc9fc3b3e89d90d9a0e38bae05445ce9e65faf47acea3ac658e5f42566def473）
  交叉核验：release 产物为上游 CI 用 sass 编译的最终主题文件。
- **LICENSE**：https://raw.githubusercontent.com/lassekongo83/adw-gtk3/v6.5/LICENSE
  SHA256 20c17d8b8c48a600800dfd14f95d5cb9ff47066a9641ddeab48dc54aec96e331，
  与源码 tag 内 LICENSE 逐字节一致（LGPL-2.1）。

## 构建说明
- 上游构建系统为 Meson + sass（SCSS → CSS）。构建主机无 sass 且
  ninja 不可执行，与 OHOS 构建环境一致；官方 release tarball 已包含
  全部编译产物，故采用数据包方式（同 adwaita-fonts 先例）：
  - `source()`：下载官方 release tarball + 单独下载 LICENSE（SHA256 校验）
  - `build()`：无需编译（数据包）
  - `package()`：安装 share/themes/adw-gtk3（light）与
    share/themes/adw-gtk3-dark（dark）+ share/licenses/adw-gtk3/LICENSE
  - `package_info()`：主题数据包，无 cpp_info
- 无需补丁，无依赖。

## 上游测试统计
- **上游自动化测试数量**：0（零）
- **依据**：
  - 源码 tag 内无 `test/` 或 `tests/` 目录
  - meson.build / src/**/meson.build 中无 test() / meson.add_test() 定义
    （仅 sass custom_target 与 install_data）
  - 上游无 .github/workflows/ CI 测试 job（release 由 GitHub Actions 构建产物）
  - 主题数据包无二进制 CLI 入口
- 消费者测试由 test_package/test_theme.py 补齐（见下）。

## 验证结果
- **conan-verify adw-gtk3 6.5**：见 reports/（G0-G4/L2/L4/L5）
- **test_package**：22 个消费者断言（index.theme light/dark 有效、
  gtk-3.0/gtk-4.0 CSS 非空、assets 资产、thumbnail、LICENSE）
- **finish adw-gtk3 6.5 built**：已完成

## 特殊说明
- 数据包类型 `package_type = "application"`，无 `cpp_info`。
- 使用 Conan 2 `get()/download()` 下载源码与许可证，遵循 SHA256 校验。
- 无 patches、无 wrapper、无本机路径进入归档。
---

**编译结束**: 2026-08-09 21:41
**最终状态**: built
