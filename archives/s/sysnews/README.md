# sysnews — 系统新闻显示工具

`news` 命令用于在用户登录时显示系统新闻：新闻文章是目录（默认 `/var/sysnews`）中的一个个文件，文件名即标题。

## 功能概述

- 显示自上次阅读（`$HOME/.news_time`）以来的新文章，`-a` 显示全部
- `-n`/`-l`/`-d`/`-D` 只列出标题、每行一个、带日期戳、自定义日期格式
- `-f DIR` 使用其它新闻目录；`-e DAYS` 清理过期文章
- `-p` 通过 `$PAGER` 分页显示

## OHOS 适配要点

- 纯 Makefile，无 configure；配方命令行覆盖 `CC`
- 上游 `make install` 需要 root（`install -o bin -g bin`），配方在 `package()` 中直接复制 `news` 与 `news.1`
- `news.c` 缺少 `<time.h>`，在 aarch64 上 `ctime`/`gmtime` 返回值被当作 `int` 截断，导致 `-a`/`-d` 段错误，由补丁 `0001-news.c.patch` 修复
- 源码取自 Debian `orig` 包（`+ds` 重打包，仅去除无关文件）：README 中记载的原站 link.xs4all.nl 本次探测无响应
