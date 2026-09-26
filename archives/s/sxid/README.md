# sxid

> s[ug]id 文件与目录审计工具（setuid/setgid 变更检测 + SHA-256/inode 跟踪）。

## 简介

`sxid`（suid, sgid file and directory checking）用于周期性审计系统中带
setuid/setgid 位的文件与目录：

- 按配置的 `SEARCH` 路径递归扫描，`EXCLUDE`/`IGNORE_DIRS` 排除子目录；
- 记录每个条目的属主/属组/模式；**目录按 inode、普通文件按 SHA-256** 跟踪；
- 与上次运行留下的日志对比，报告新增（`+`）、移除（`-`）以及属性/校验和/inode
  变化（`m`/`i`）；
- `FORBIDDEN` + `ENFORCE` 可对禁止路径强制去掉 s 位；
- 报告默认邮件发送；`-n` 输出到 stdout，`-k` 对当前目录做 spotcheck，`-l` 列出全部条目。

它常由 root 的 cron 每日运行，用来发现被植入的 setuid rootkit（改名/换权限
但校验和不同）以及误加 s 位的文件。

## OHOS 适配要点

- 上游是 autotools 工程但无测试套件；本配方直接用 OHOS clang 编译 6 个 C 源文件，
  并生成 `configure` 本会产出的 `config.h`，绕开 autoreconf/automake/config.guess。
- `getopt_long_only` 由 OHOS bionic 提供，随包 GNU getopt 不参与编译；无第三方依赖。
- **平台差异**：OHOS/HMDFS 上普通文件无法保存 S_ISUID/S_ISGID（`chmod` 成功但位被静默
  剥离），目录则被强制 SGID。因此 sxid 在 OHOS 上发现不了 setuid 普通文件，却会把
  子目录都视为 setgid 条目。详见 `4.20130802/notes.md`。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| 无 | — | 仅需 C 标准库（含 bionic 的 `getopt_long_only`） |

## 功能验证

```bash
# 审计一个受控目录（配置里 SEARCH/LOG_FILE/EXTRA_LIST 指向可写路径）
sxid -n -c /path/to/sxid.conf      # 输出到 stdout
sxid -n -l -c /path/to/sxid.conf   # 额外列出全部条目
cd /some/dir && sxid -n -k -c /path/to/sxid.conf   # spotcheck 当前目录
sxid -V
```

## 参考

- [源码仓库](https://github.com/taem/sxid)
- [Debian 源码包](https://packages.debian.org/source/sxid)
