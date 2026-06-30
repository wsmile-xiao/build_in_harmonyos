# pg_top

pg_top 是一个类似 top 的 PostgreSQL 数据库活动监控工具。

## 功能概述

- 实时显示 PostgreSQL 进程和查询活动
- 支持按 CPU、内存等维度排序
- 提供类似 top/htop 的终端界面

## OHOS 适配

- **构建系统**: cmake
- **主要补丁**: CMakeLists.txt 配置修复 + 新增 harmonyos 机器类型识别 + screen.c 平台适配
- **依赖**: PostgreSQL, ncurses, libbsd, libmd, libintl

## 依赖关系

- PostgreSQL (9.4.13+)
- ncurses (6.4)
- libbsd (0.11.7)
- libmd (1.1.0)
- libintl (8)

## 参考资料

- 官网: https://gitlab.com/pg_top/pg_top