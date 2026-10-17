# ldap-git-backup — OpenHarmony 编译档案

## 软件简介
ldap-git-backup 是 Elmar Heeb 的 LDAP 备份工具：将 LDAP 目录的 LDIF 导出
快照提交到 Git 仓库。由于 LDAP 目录写操作稀少且每次只改少量条目，Git 的
增量存储能以极省空间的方式保留目录的完整变更历史。默认导出命令为
OpenLDAP `slapcat`（可用 `--ldif-cmd` 换成任意 LDIF 导出命令），另附
`safe-ldif` slapcat 安全包装脚本。上游为 autotools 包装的两个纯 Perl
脚本（无编译），许可证 GPL-3.0-or-later。

## OHOS 适配要点
- 纯 Perl 脚本包：上游 configure/Makefile 仅做 `@VAR@` 替换与 chmod，
  配方在 build() 以 Python 等价实现，**无需 autoconf/automake**（OHOS
  真机无 autotools）
- 运行时依赖：perl（核心模块 + git 自带的 Git.pm）与 git；perl 走仓库
  已适配包 perl/5.42.2.3（runenv 注入 PATH/PERL5LIB），git 为设备系统
  工具
- 上游测试套件 `t/`（11 个 prove 用例，mock-slapcat 假 LDAP 导出，无需
  真实 LDAP 服务）按原相对布局随包安装于 share/ldap-git-backup/，
  消费者 `cd share/ldap-git-backup && prove t` 原样复跑
- 脚本默认 `--ldif-cmd` 指向包内 safe-ldif（`@sbindir@` 替换为包 bin/）；
  默认备份目录 /var/backups/ldap 在 OHOS 上可用 `--backup-dir` 指定
  可写路径

## 依赖关系
- 运行时: perl/5.42.2.3（仓库已适配）、git（系统工具）
- 被依赖: 无（独立 CLI 工具）

## 参考资料
- [elmar/ldap-git-backup (GitHub)](https://github.com/elmar/ldap-git-backup)
- [Debian 源码包 ldap-git-backup](https://packages.debian.org/source/sid/ldap-git-backup)
