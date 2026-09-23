# nmail

终端 Email 客户端（Email UA），基于 ncurses 的 TUI 界面，支持 IMAP/SMTP、
全文搜索（Xapian）、多账户与 OAuth2。上游：https://github.com/d99kris/nmail

## 功能

- ncursesw TUI 邮件读写界面（-h 帮助 / -v 版本为纯 IO 退出路径）
- IMAP 收件 + SMTP 发件，支持 Gmail/iCloud/Outlook 内置向导
- Xapian 全文搜索 + SQLite 本地缓存
- SASL 认证（PLAIN/LOGIN 等，cyrus-sasl 2.1.28.1）

## 版本

| 版本 | 状态 | 适配日期 | Conan 引用 |
|------|------|----------|------------|
| 5.14.12 | built | 2026-09-11 | nmail/5.14.12 |

## HarmonyOS PC 适配要点

详见 `5.14.12/notes.md`。核心：

- libetpan 走 vendored（ext/libetpan 内嵌编译），notmuch 非依赖（源码零引用）
- 依赖全走 ohpcd 制品仓，cyrus-sasl 用 2.1.28.1 规避 openssl 版本冲突
- CMake 大写变量由 conanfile generate() 显式注入绝对路径
