# surfraw

Shell Users' Revolutionary Front Rage Against the Web

## 软件简介

Surfraw 是一个命令行搜索引擎前端工具，提供了 100+ 个搜索引擎接口（elvi），允许用户直接从命令行发起搜索，无需打开浏览器手动输入。支持 Google、Wikipedia、YouTube、Bing、DuckDuckGo 等主流搜索引擎。

- **主页**: https://gitlab.com/surfraw/Surfraw
- **许可证**: LicenseRef-Homebrew-public-domain
- **语言**: Shell (bash) + Perl
- **构建系统**: autotools

## 已编译版本

| 版本 | 状态 | 日期 | 补丁数 |
|------|------|------|--------|
| 2.3.0 | built | 2026-06-24 | 4 |

## 关键文件

- 可执行文件: `bin/surfraw`, `bin/sr` (别名), `bin/surfraw-update-path`, `bin/opensearch-discover`, `bin/opensearch-genquery`
- 搜索引擎接口: `lib/surfraw/` (113 个 elvi 脚本)
- 配置文件: `etc/xdg/surfraw/conf`, `etc/xdg/surfraw/bookmarks`
- 手册页: `share/man/man1/` (surfraw.1, sr.1.gz, elvi.1sr 等)
