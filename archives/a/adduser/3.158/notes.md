# adduser 3.158 适配笔记

## 上游真源码包

- URL: https://deb.debian.org/debian/pool/main/a/adduser/adduser_3.158.tar.xz
- sha256: 92dbed2ede56270e92289a05154856fd7332bb466bee0e27d8767019fbf30e69
- 下载验证: 371620 字节真 xz 包，解压含 work/ 目录（adduser/deluser/addgroup/delgroup 脚本 + Adduser*.pm 模块）

## 构建系统

adduser 是纯 Perl CLI 工具，无 Makefile/configure/编译，构建系统为 "none"。
配方 package 段直接复制脚本到 bin/ + 模块到 lib/perl5/adduser/ + 配置到 etc/。

## 上游测试案例

- testsuite/test01.pl ~ test10.pl（10 个 Perl 测试脚本）
- debian/tests/f/*.t（多场景测试：account_locks/addgroup_2_args/backups/clones 等）
- debian/tests/ecryptfs/*.t（加密 home 目录测试，需 ecryptfs-utils 包）
- 上游测试需 root 权限 + 真系统用户管理操作（adduser --system 创建系统用户），CI 环境无法跑

## 适配后新增测试案例

- test_package/conanfile.py test() — 验证 adduser/deluser 脚本存在 + perl -c 语法检查
- perl -c 不需真执行只验语法（避 root 权限 + 真系统用户管理操作）
- 需 PERL5LIB 包含 Adduser*.pm 模块路径避 use AdduserCommon 找不到
- 通过率：1/1 = 100%

## 依赖

- perl（运行时依赖，纯 Perl 脚本工具）
- 无外部库依赖（Adduser*.pm 模块随包附带）

## 鸿蒙特有适配

- 鸿蒙 OHOS arm64 支持（validate 段验 settings.os in Linux/OHOS + settings.arch in armv8/arm64）
- 无补丁（纯 Perl 脚本，无需适配鸿蒙特有 API）
