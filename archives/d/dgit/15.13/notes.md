# dgit 15.13 适配笔记

## 编译环境
- 构建系统: Perl 脚本（无需编译）
- 编译日期: 2026-08-08
- 编译器: N/A (Perl script package)
- 状态: built

## 软件概述

dgit 是用于在 Git 仓库中维护 Debian 软件包的 Perl CLI 工具。它可以让用户：
- 将 Debian 归档视为 Git 仓库
- 从 Git commits 构建上传包 (`dgit push`)
- 从上传包构建 Git commits (`dgit clone` / `dgit fetch`)

## 构建步骤

dgit 是纯 Perl 脚本包，无需编译：

1. 从 salsa.debian.org 下载源码（CI Worker 可达；snapshot.debian.org 与 deb.debian.org 不可达/404）
2. 解压源码包
3. 复制脚本到 bin/
4. 复制 Perl 模块到 lib/
5. 复制共享文件到 share/dgit/

## 源码结构

源码包根目录为 `work/`，包含：
- 主脚本：`dgit`, `git-debrebase`, `git-debpush`, `git-deborig`, `git-playtree-setup` 等
- Perl 模块：`Debian/Dgit.pm`, `Debian/Dgit/*.pm`
- 共享文件：`dgit-functions.sh`
- 基础设施脚本：`infra/`
- 测试：`tests/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原始源码 URL 返回 404 | dgit 15.13 已被 16.3 取代，从 Debian pool 移除 | 使用 salsa.debian.org 官方 git 归档（CI Worker 可达） |
| 2 | dgit CLI 无法运行 | `Debian::Dgit` 依赖 `Dpkg::Control::Hash`，OHOS 无此模块 | 打包脚本和模块，文档说明限制 |
| 3 | JSON 模块缺失 | OHOS Perl 仅有 JSON::PP，无 JSON 包装模块 | 不影响打包，仅影响运行时 |
| 4 | Dpkg 模块缺失 | OHOS 不是 Debian 系统，无 dpkg-dev | 文档说明为已知限制 |

## 真机环境

- HarmonyOS aarch64
- Perl 5.42.0 (`/data/service/hnp/bin/perl`)
- git 2.45.2 (`/data/service/hnp/bin/git`)
- Digest::SHA: 可用
- JSON::PP: 可用
- Dpkg: 不可用

## 源码修改

无源码修改（Perl 脚本包）

## 验证

- Conan `create`：通过
- Conan `test_package`：验证脚本安装和 Perl 模块加载
- 上游测试：未执行（137 个测试均为 Debian 环境集成测试，OHOS 不适用）

## 注意事项

- dgit 是 Debian 特定工具，需要完整的 Debian 打包工具链才能完全运行
- `Debian::Dgit` 模块依赖 `Dpkg::Control::Hash`，该模块在 OHOS 上不可用
- `Debian::Dgit::ExitStatus` 模块不依赖 Dpkg，可以正常加载
- 需要 PERL5LIB 环境变量正确设置
- 源码 URL 使用 salsa.debian.org 官方 git 归档（CIWorker 可达；snapshot.debian.org 不可达）
