# adwaita-fonts 50.0 适配笔记

## 基本信息
- **软件名称**：adwaita-fonts
- **版本**：50.0
- **构建系统**：Meson
- **许可证**：OFL-1.1
- **上游仓库**：https://gitlab.gnome.org/GNOME/adwaita-fonts

## 构建说明
- 纯字体数据包，Meson 只做 `install_data()`，安装 6 个 .ttf 文件到 `share/fonts/Adwaita/`。
- 无需编译，字体文件在上游已预构建。
- 4 个 Mono 字体（AdwaitaMono-Bold/Italic/Regular + BoldItalic），2 个 Sans 字体（AdwaitaSans-Regular/Italic）。
- 无构建依赖，无运行时依赖。

## 源码 URL
- **当前 URL**：https://gitlab.gnome.org/GNOME/adwaita-fonts/-/archive/50.0/adwaita-fonts-50.0.tar.gz
- **SHA256**：2445748089284b66e6352b529f36d366b49b2ba023ddc4a8ad13217cadd72cc2
- **官方 URL**：https://download.gnome.org/sources/adwaita-fonts/50/adwaita-fonts-50.0.tar.xz
- **官方 SHA256**：4c927fbfeec1c503801ba510c2c94e0054c82c522cf7ba0d3be5d4d41fcf5c86
- **说明**：官方 `download.gnome.org` 在本地网络持续 connection reset/timeout，不可达，因此使用 GitLab tag 50.0 archive 作为最终 URL。CI 环境网络可能不同，可切换为官方 URL。

## 上游测试统计
- **上游自动化测试数量**：0（零）
- **依据**：
  - 项目无 `test/` 或 `tests/` 目录
  - 无任何测试框架引用（无 pytest、unittest、go test 等）
  - `.gitlab-ci.yml` 仅包含 GNOME CI 模板，无 test job
  - 项目是纯字体数据包，仅包含 6 个 .ttf 文件 + meson.build + LICENSE + README

## 验证结果
- **conan-verify adwaita-fonts 50.0**：退出码 0，G0/G1/G2/G3/G4/L2/L4/L5 全部 PASS
- **W3 本地 CI 模拟**：通过
- **test_package**：1 个 test() 方法，18 个断言（6 个文件存在 + 6 个非空 + 6 个 TTF magic），全部通过
- **finish adwaita-fonts 50.0 built**：已完成

## 特殊说明
- 数据包类型 `package_type = "application"`，无 `cpp_info`。
- 使用 `conan.tools.files.copy` 安装字体文件，遵循 Conan 2 API。
- 无需补丁，无需修改上游源码。
---

**编译结束**: 2026-08-05 06:38
**最终状态**: built
