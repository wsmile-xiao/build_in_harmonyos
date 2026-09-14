# debsigs 0.2.2 适配笔记

## 编译环境
- 构建系统: custom（纯 Perl 脚本，无编译）
- 上游仓库: https://gitlab.com/debsigs/debsigs（release/0.2.2）
- 源码包: https://deb.debian.org/debian/pool/main/d/debsigs/debsigs_0.2.2.orig.tar.xz
- 校验: sha256 11441c9946786bc4b6f5eed8f9301d78f3fcbcbfbb1ea082044459d8e45a9c00（md5 1b467122b521bb1e846cfbaba9925555 与 .dsc 一致，tar 内 73 个条目已核验）
- 编译日期: 2026-09-10
- 状态: built（待真机预检）

## 上游结构与测试清点
- `perl/`：debsigs、debsigs-autosign、debsigs-installer、debsigs-signchanges（可执行）+ arf.pm、debsigsmain.pm（VERSION v0.2.2）、forktools.pm、gpg.pm + Makefile.PL（ExtUtils::MakeMaker，仅用于 Debian 打包）。
- 上游测试：
  - `perl/test.pl`：Test::More 4 用例（use_ok arf/debsigsmain/forktools/gpg），仅需 perl，可在真机运行，已接入 conanfile build()。
  - `python/tests/testsigs/unit/`：pytest 6 用例（test_autosign 1、test_debsigs 2、test_features 1、test_installer 1、test_signchanges 1），需 gnupg + debsig-verify + sqop + 在线构建 dpkg 测试包，OHOS 缺失这些组件，未在真机运行（见 PR 补充说明）。

## 编译步骤
1. `download()` 拉取 orig.tar.xz（sha256 校验），`tar -xJf --no-same-owner` 解压后收拢（沿用 debhelper/dpkg 模式，规避沙箱 get() PermissionError）。
2. `build()` 用真机 perl 运行 `perl/test.pl`，解析 `ok/not ok` 行统计 4 用例，输出 `HMBS_UPSTREAM_TEST_RESULT`（framework perl-Test-More）并持久化到 `build_folder/hmbs_upstream.json`。
3. `package()` 将 4 个脚本装入 `bin/`（chmod 755），4 个 `.pm` 装入 `lib/perl5/Debian/debsigs/`，COPYING 装入 `licenses/`，hmbs_upstream.json 随包带入 `res/` 供 test_package 缓存命中时复发。
4. `test_package/test_debsigs.py` 执行真实二进制：`debsigs --version` 期望 `debsigs v0.2.2`，`debsigs --features` 的 debsigs 条目版本一致；2 个检查点，输出 `HMBS_TEST_PACKAGE_RESULT`。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan get()` 在沙箱抛 PermissionError | HMDFS/沙箱限制（debhelper/dpkg 同因） | 改用 `download()` + 手动 `tar --no-same-owner` + `cp -a` 收拢 |
| 2 | 无 Makefile/CMake，conan 模板不适用 | 纯脚本工具 | custom 配方：拷贝安装，不做编译 |
| 3 | 缓存命中时 build() 跳过导致上游证据消失 | Conan 缓存机制 | build() 双通道输出标记并落盘，package() 带入 res/，test_package 每轮复发 |

## 依赖版本
- 构建依赖：无（仅需 perl 解释器，真机 /data/service/hnp/bin/perl）。
- 运行依赖：perl；签名/验签功能需 gpg（消费者按需提供，不在配方中硬依赖）。

## 验证结果
- 本地（Windows）：配方静态检查通过（conanfile 无残留占位符，conandata sha256 与 .dsc md5/sha1 交叉核验一致）。
- 真机预检：待 HMBS 后台执行（conan create + test_package + perl/test.pl 4 用例 + test_debsigs.py 2 检查点），数字以预检日志为准。

## 注意事项
- `debsigs --verify` 需外部 `debsig-verify` 程序，OHOS 未提供，test_package 不覆盖该路径。
- test_installer 上游为 NotImplementedError，计入未运行 6 用例之一，不纳入通过率。
