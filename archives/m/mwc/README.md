# mwc

> MailWebsiteChanges — 网站变化追踪工具（邮件通知 + RSS feed）

## 基本信息

| 项目 | 内容 |
|------|------|
| 上游版本 | 2.0.5 |
| 许可证 | GPL-2.0-or-later |
| 主页 | https://github.com/mtill/MailWebsiteChanges |
| 源码 | https://github.com/mtill/MailWebsiteChanges/archive/refs/tags/v2.0.5.tar.gz |
| 构建系统 | 纯 Python 3 脚本（无 setup.py，无编译） |
| 依赖 | Python 3 + lxml + cssselect（pip vendor 进包内 deps/） |

## 描述

mwc 按 XPath / CSS 选择器 / 正则监控网页内容变化，变化时发送邮件通知并/或生成 RSS 2.0 feed。可配置为 cron 定时任务运行。

## 支持版本

| 版本 | 状态 | 构建系统 |
|------|------|---------|
| 2.0.5 | built | python |

## 用法

```sh
mwc.py --config=<配置模块> [--dry-run=<站点名>]
mwcfeedserver.py --config=<配置模块> --bind=localhost --port=8000
```
