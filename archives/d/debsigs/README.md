# debsigs

## 简介
debsigs 是 Debian .deb 软件包的签名管理工具，用于创建、列出、删除和校验 .deb 内的密码学签名（origin/maint 等类型），由纯 Perl 脚本实现。

## OHOS 适配
- 纯 Perl 脚本，无原生编译：4 个可执行脚本装入 `bin/`，4 个 `Debian::debsigs::*` 模块装入 `lib/perl5/Debian/debsigs/`。
- 沙箱下 `conan get()` 会抛 PermissionError，沿用 debhelper/dpkg 的 `download()` + `tar --no-same-owner` 模式。
- 上游 `perl/test.pl`（Test::More 4 用例）在 `build()` 中用真机 perl 实际运行。
- 上游 pytest 功能套件（6 用例）需 gnupg + debsig-verify + sqop，在 OHOS 未运行，如实声明。

## 依赖
- 构建/运行：perl（真机 /data/service/hnp/bin/perl）。
- 签名/验签功能运行时需 gpg / debsig-verify（消费者按需提供，配方不硬依赖）。

## 功能验证
```bash
PERL5LIB=<pkg>/lib/perl5 perl <pkg>/bin/debsigs --version  # 期望输出: debsigs v0.2.2
PERL5LIB=<pkg>/lib/perl5 perl <pkg>/bin/debsigs --features
```

## 参考
- 官网: https://gitlab.com/debsigs/debsigs
- 源码: https://deb.debian.org/debian/pool/main/d/debsigs/debsigs_0.2.2.orig.tar.xz
