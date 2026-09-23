# cvs-mailcommit 1.19 适配笔记（HarmonyOS PC · 纯 Perl 工具打包）

## 定位
- cvs-mailcommit 是 Debian 维护的 CVS 提交邮件通知脚本（Perl 实现，提交时发送 log + diff 邮件）。
- 上游形态：单个 Perl 脚本 + Debian 打包，无 C 编译产物、无构建系统 → 走纯脚本打包路径（参照 cvsweb 3.0.6、colordiff 1.0.21-r0）。
- 版本策略：首次适配，直接使用上游版本 1.19（R37）。

## 源码
- 官方源：Debian 软件池 `pool/main/c/cvs-mailcommit/` 的 `cvs-mailcommit_1.19.orig.tar.gz`（Debian 维护脚本，无独立上游发布包，Debian 池即官方源）。
- conandata.yml 提供 deb.debian.org 主源 + ftp.debian.org 回退，同一 sha256 校验。
- sha256 说明：本机到 Debian 网络受限（仅 GitCode 可达），当前值为待真机核验占位；HMBS 真机预检的下载校验若报 mismatch，按日志中的实际哈希更新后重新验证。

## 关键适配
- 无编译：`build()` 仅做 `perl -c` 语法自检（OHOS perl 位于 `/data/service/hnp/bin/perl`，`PERL` 环境变量可覆盖），与 cvsweb 一致。
- 文件名归一化：Debian 原包顶层脚本名可能为 `cvs-mailcommit` 或 `*.pl`，`package()` 统一安装为 `bin/cvs-mailcommit` 并 chmod 755。
- settings 取四项全量（os/arch/compiler/build_type）以通过 L0p 门禁；纯脚本包无 libs，`package_type=application`，`bindirs=["bin"]`。
- R38：命令行工具，在软件级目录提供 `commands.json`（type=tool）。
- R26：无 `.so` 产物，系统同名库隔离不适用。
- R39：URL 为 Debian 官方池 https 源，无个人 fork/CDN。

## 上游测试审计
- 上游无测试套件：单个脚本 + `debian/` 打包，无 `tests/`、无 `make check`/`ctest`/`pytest` 入口（类比 cvsweb 3.0.6 `upstream_tests: []`）。
- `test_package/MANIFEST.yml` 已按 HMBS 要求写入 `upstream_tests_exist: false` 与非空 `upstream_test_audit`。
- 配方 `build()` 在语法自检后输出 `HMBS_UPSTREAM_TEST_RESULT`（`status:no_tests`，`discovered/executed:0`，附 reason）。
- test_package 三断言：文件存在且可执行、`perl -c` 通过、功能运行有输出；测试脚本末尾输出 `HMBS_TEST_PACKAGE_RESULT`（discovered=3）。

## 编译验证
- 本机未运行 conan（按任务守则，验证转由 HMBS 真机预检执行）。
- 待真机回填：`conan create` 结果、上游标记与 test_package 标记原文、产物清单。

## 交付物
- `bin/cvs-mailcommit`（Perl 脚本，可执行）
- `share/man/man1/*`（上游自带手册页，如有）
- `share/doc/cvs-mailcommit/*`、`licenses/*`（上游文档与许可，如有）

## 注意事项
- 运行时依赖：系统 perl（OHOS 自带）与 `/usr/sbin/sendmail` 兼容 MTA（按 CVS 服务器配置）；本包仅交付脚本。
- 若 Debian 原包解压后无顶层根目录（扁平文件），`strip_root=True` 可能需改为 False，以真机 `get()` 日志为准调整。
