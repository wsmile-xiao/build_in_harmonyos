# outils

outils 是 Leah Neukirchen 维护的 OpenBSD 非标准工具移植集（版本 0.14），把 OpenBSD 的
apply / calendar / cksum / jot / lam / lndir / md5 / rdate / rs / signify / ts /
unvis / vis / what 等工具移植到 Linux 平台。

## 功能概述
- 校验和工具：md5 / cksum / sha1 / sha256 / sha512（同一二进制按 argv[0] 分派）
- 文本处理：jot / lam / rs / ts / vis / unvis / what / apply
- 日历提醒：calendar（支持 #include 日历文件、-f / -t / CALENDAR_DIR）
- 数字签名：signify（内嵌 ed25519 + bcrypt_pbkdf，无外部加密库依赖）
- 目录工具：lndir（影子目录）
- 时间工具：rdate（RFC868 / NTP）

## OHOS 适配
- 纯手写 Makefile 项目，无 configure；`make CC=clang -j1`
- 上游 Makefile 在 glibc 环境下依赖 libc 提供 explicit_bzero / reallocarray / adjtime，
  musl（HarmonyOS）缺失 → 补丁补齐链接对象并新增 adjtime(3) 兼容实现（clock_adjtime）
- calendar 默认通过外部 C 预处理器（/usr/bin/cpp）展开 #include；HarmonyOS 无 cpp
  → 补丁改为内置 #include 展开（保留 -I 搜索语义），数据文件随包安装到 share/calendar
- md5 别名（cksum/sha1/sha256/sha512）以真实副本安装，规避 HMDFS 软链接限制

## 依赖关系
- **编译依赖**: 无（仅 libc/libm + 自带可移植代码）
- **运行依赖**: 无

## 参考资料
- 上游: https://github.com/leahneukirchen/outils
