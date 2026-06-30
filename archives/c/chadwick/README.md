# Chadwick

棒球计分和记分工具集，提供 Retrosheet 格式的棒球比赛数据解析和处理功能。

## 功能概述

- **cwevent**: 生成事件级数据（CSV/Fortran 格式），每条记录描述一个比赛事件
- **cwgame**: 生成比赛级数据描述，每条记录描述一场完整比赛
- **cwbox**: 从 play-by-play 数据生成比赛记录（boxscore），支持 XML 和 SportsML 输出
- **cwcomment**: 从比赛文件中提取注释信息
- **cwdaily**: 生成球员逐场比赛数据
- **cwsub**: 生成球员替换记录

## 库

- **libchadwick**: C 语言静态库，提供棒球数据解析的核心 API

## OHOS 适配

- **config.guess/config.sub**: 原始版本（2020年）不支持 HarmonyOS 平台检测，需替换为 automake-1.17 版本
- **umask 问题**: HMDFS 文件系统上 `umask 077` 会创建 SGID 目录（drwx--S---），导致后续文件写入失败，需将 `umask 077` 改为 `umask 022`
- **autoreconf**: 原始 configure 脚本与系统 automake 版本不匹配，需运行 `autoreconf -fi` 重新生成构建系统
- **静态链接**: 作为终端工具，按 R26 要求使用 `--enable-static --disable-shared` 和 `-static` 进行静态链接

## 依赖关系

- 无编译依赖
- 无运行时依赖（静态链接后仅依赖 musl libc）

## 参考资料

- 官网: https://github.com/chadwickbureau/chadwick
- Retrosheet 格式文档: https://www.retrosheet.org/

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [0.10.0](./0.10.0/) | built | 2026-06-26 |
