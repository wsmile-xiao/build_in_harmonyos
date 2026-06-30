# libdshconfig

## 软件描述

libdshconfig 是一个用于读取 dsh (dancer's shell / distributed shell) 配置文件格式数据文件的 C 库。

它提供以下 API：
- `open_dshconfig(FILE*, char delimiter)` — 打开并解析配置文件
- `dshconfig_searchdata(const dshconfig*, const char* index)` — 按键名搜索配置数据
- `dshconfig_splitline(const char* original, char delimiter)` — 按分隔符分割行
- `free_dshconfig(dshconfig*)` / `free_dshconfig_internal(dshconfig_internal*)` — 释放内存

## 软件信息

| 项目 | 值 |
|------|------|
| 名称 | libdshconfig |
| 版本 | 0.20.13 |
| 许可证 | GPL-2.0-or-later |
| 构建系统 | autotools |
| 语言 | C |
| 主页 | https://www.netfort.gr.jp/~dancer/software/ |
| 依赖 | 无 |

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 0.20.13 | published | 2026-06-26 |
