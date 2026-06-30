# cdb

## 软件描述

Cdb 是一个快速、可靠、简单的常量数据库创建和读取工具包，由 D.J. Bernstein (DJB) 开发。

常量数据库是指创建后不可修改的数据库——所有更新都需要重建整个数据库。这种设计使得查询非常快速：一次磁盘 seek 即可检索任意记录。

## 主要工具

| 工具 | 功能 |
|------|------|
| cdbmake | 从标准输入创建 cdb 数据库 |
| cdbget | 从 cdb 数据库中查询指定键的值 |
| cdbdump | 转储 cdb 数据库内容 |
| cdbstats | 统计 cdb 数据库信息 |
| cdbtest | 测试 cdb 数据库完整性 |
| cdbmake-12 | 从 /etc/services 格式创建 cdb |
| cdbmake-sv | 从 SV 格式创建 cdb |

## 版本信息

| 版本 | 实际版本 | 日期 | 状态 |
|------|----------|------|------|
| 20251021 | 0.75 | 2026-06-30 | built |

## 构建系统

cdb 使用 DJB 自定义构建系统（非 autotools/cmake）：
- 通过 `conf-cc` 指定编译器
- 通过 `conf-ld` 指定链接器
- 通过 `conf-home` 指定安装路径
- `make` 构建所有工具

## 许可证

Public domain（公有领域）

## 主页

https://cr.yp.to/cdb.html
