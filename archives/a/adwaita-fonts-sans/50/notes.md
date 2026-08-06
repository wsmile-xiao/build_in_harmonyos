# adwaita-fonts-sans 50 适配笔记

## 编译环境
- 构建系统: none（纯字体数据包 noarch，无需构建系统，仅复制 .ttf 文件）
- 编译日期: 2026-08-05
- 编译器: 无需编译（纯字体数据包）
- 状态: built

## 编译步骤

adwaita-fonts-sans 是纯字体数据包，无需编译。Conan 配方直接：
1. 下载上游 GNOME 源码归档
2. 提取 sans/ 目录下的 .ttf 文件
3. 安装到 share/fonts/Adwaita/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI Worker 无法直连 GitHub 下载源码 | CI Worker 网络限制，GitHub 镜像代理（ghproxy/gitclone/kkgithub）均 5xx 或超时 | 改用 GNOME 官方源 https://download.gnome.org/sources/adwaita-fonts/50/adwaita-fonts-50.0.tar.xz（sha256 已真实下载验证） |
| 2 | 本地开发环境 GNOME 官网连接不稳定 | 境外源网络延迟高 | 本地开发时使用预先下载的 tarball 或 GitLab 镜像 |

## 源码信息

- 最终源码 URL: https://download.gnome.org/sources/adwaita-fonts/50/adwaita-fonts-50.0.tar.xz
- SHA256: 4c927fbfeec1c503801ba510c2c94e0054c82c522cf7ba0d3be5d4d41fcf5c86（真实下载后重新计算，与 download.gnome.org 官方 .sha256sum 一致）
- 镜像说明: gitcode.com 无 adwaita-fonts 镜像（已探测 gh_mirrors/github_mirrors/mirror_store/src-openeuler 均不存在）；GitHub 及 gh-proxy 因 CI Worker 不可达弃用；GNOME 官方源在 CI Worker 网络中可达

## 依赖版本

无编译依赖。

## 验证结果

| 验证 | 退出码 | 结果 |
|------|--------|------|
| conan create（含 test_package） | 0 | ✅ PASS |
| conan-verify（G0-G4 + L2/L4/L5） | 0 | ✅ PASS |
| 本地 CI 模拟（setup.sh + build_and_test.sh） | 0 | ✅ PASS |
| finish adwaita-fonts-sans 50 built | 0 | ✅ PASS |

## 交付物

| 文件 | 说明 |
|------|------|
| share/fonts/Adwaita/AdwaitaSans-Regular.ttf | Adwaita Sans 常规体 |
| share/fonts/Adwaita/AdwaitaSans-Italic.ttf | Adwaita Sans 斜体 |

## 注意事项

- 上游 adwaita-fonts 项目包含 sans 和 mono 两个子目录，本包仅打包 sans 字体
- 许可证：SIL Open Font License 1.1 (OFL-1.1)，上游许可证文件 LICENSE 已安装到 share/licenses/adwaita-fonts-sans/LICENSE
- 构建系统为 none：本包为纯字体数据包（noarch），无 configure/make/编译步骤，Conan 配方仅下载源码归档并复制 .ttf 文件到 share/fonts/Adwaita/
- 上游 GitLab 仓库：https://gitlab.gnome.org/GNOME/adwaita-fonts
- GitHub 镜像：https://github.com/GNOME/adwaita-fonts
---

**编译结束**: 2026-08-05 18:01
**最终状态**: built
