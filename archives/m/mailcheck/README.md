# mailcheck

Check multiple mailboxes and/or Maildirs for new mail. Supports mbox and
Maildir formats, plus remote POP3 and IMAP mailboxes.

## 编译信息

- **官方主页**: https://mailcheck.sourceforge.net/
- **构建系统**: Makefile (plain, no configure)
- **编译器**: clang
- **依赖**: 无外部依赖（纯 C 标准库）

## 已编译版本

- 1.91.2 (2026-08-30) - 状态: built

## 使用方法

mailcheck 读取 `~/.mailcheckrc`（不存在时回退到 `/etc/mailcheckrc`），
检查其中列出的每个邮箱路径（mbox 文件、Maildir 目录、`pop3:`/`imap:` URL）。

## 上游测试

上游 1.91.2 发布 tarball **不含**任何测试套件：Makefile 仅有
`all/debug/mailcheck/install/distclean/clean` 目标，无 `check`/`test` 目标；
无 `tests/` 目录、无 `configure` 脚本、无 CI 配置。test_package 中的测试
为包级补充测试，不冒充上游测试。
