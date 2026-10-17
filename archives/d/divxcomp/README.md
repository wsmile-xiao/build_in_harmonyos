# divxcomp

divxcomp 是一个 DivX 电影码率计算器，为纯 Perl/Tk GUI 脚本（单文件
`divxcomp.pl`，104 行，上游 2003 年发布，唯一版本 0.1）。上游主页早已
失效（DNS NXDOMAIN），事实上的官方分发渠道是 Debian pool /
salsa.debian.org 打包仓。

- **来源**: https://deb.debian.org/debian/pool/main/d/divxcomp/divxcomp_0.1.orig.tar.gz
- **许可证**: GPL-2（归档内含 GPLv2 全文 GPL.txt；脚本头声明 version 2 or
  any later version，Debian 元数据归类为 GPL-2，本仓沿用 Debian 口径）
- **分类**: utility / 桌面小工具

## 软件描述

输入 CD 容量（MB）与影片时长（分钟）、MP3 音轨码率（kbps），估算 DivX
视频可用的码率。逻辑极简单（`divxcompute` 子过程），但界面为 Perl/Tk。

## 运行时依赖（目标环境）

| 依赖 | 性质 | OHOS 现状 |
|---|---|---|
| perl 解释器 | 硬依赖 | 已具备：/data/service/hnp/bin/perl (5.42.0) |
| Perl::Tk + Tk::BrowseEntry | GUI 硬依赖 | 未安装（含 XS 并链接 X11，headless 环境不适用） |
| X11 display | GUI 硬依赖 | 无 |

## 适配说明

- **构建系统**: 无（单脚本分发，无任何编译步骤）
- **安装方式**: 脚本安装为 `bin/divxcomp`，打包时把 shebang
  `#!/usr/bin/perl -w` 重写为目标环境 Perl（E037: OHOS 无 /usr/bin/perl）
- **无障碍入口**: 补丁 `0001-ohos-headless-version-flag.patch` 在 `use Tk`
  之前的 BEGIN 块中处理 `--version`，headless 环境可查询版本：
  `divxcomp --version` 输出 `divxcomp 0.1`
- **GUI 限制**: 需要 Perl::Tk 与 X11 display，headless OHOS/CI 上无法启动
  图形界面；计算逻辑无法在无 GUI 环境下做端到端验证
- **测试**: 上游无任何测试套件（归档仅含 README / GPL.txt / divxcomp.pl /
  ChangeLog）；test_package 提供 `--version` headless 冒烟（自建验证，
  不冒充上游测试）

## 版本列表

| 版本 | 状态 | 适配日期 | 备注 |
|------|------|----------|------|
| 0.1 | built | 2026-09-13 | 上游唯一版本；headless 冒烟通过，GUI 需用户侧 Tk+X11 环境 |
