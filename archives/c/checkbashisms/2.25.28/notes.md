# checkbashisms 2.25.28 — OpenHarmony 移植笔记

## 适配说明

- 类型: Perl 脚本（无需编译，直接解释执行）
- 上游源码: https://salsa.debian.org/debian/devscripts
- 下载地址: https://salsa.debian.org/debian/devscripts/-/archive/v2.25.28/devscripts-v2.25.28.tar.gz
- SHA256: c9e129c1176f483175c971c39d74094494a4e54878bf9892c6bafa6e5d9dcc32
- 依赖: Perl 运行时

## 修改内容

### 补丁: 0001-fix-shebang.patch
将 shebang 从 `#!/usr/bin/perl` 改为 `#!/usr/bin/env perl`，
适配 OHOS 上 Perl 在 PATH 中的情况。

## 特殊说明

- checkbashisms 是 Perl 脚本，不需要编译，直接安装即可
- 构建过程中自动替换 ###VERSION### 占位符为实际版本号
- 上游测试需要 shunit2，在 OHOS 上可能缺失，设置 ignore_errors=True

## 验证状态

- [ ] conan-verify: 待 CI 执行
- [ ] 本地 CI 模拟: 待 CI 执行