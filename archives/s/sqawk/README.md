# sqawk

sqawk 是一个基于 SQLite 的 AWK 风格文本处理工具，用 Tcl 编写。

## 功能概述

- 使用 SQL 语法处理文本数据
- 支持 AWK 风格的字段分隔
- 基于 SQLite 引擎进行查询和聚合
- 可管道式处理文本流

## OHOS 适配

- **构建系统**: makefile（Tcl 脚本安装）
- **主要补丁**: ginstall 替代 install 命令
- **依赖**: tcl, tcllib, sqlite3-tcl

## 依赖关系

- tcl (8.6.14)
- tcllib (1.21)
- sqlite3-tcl (3.49.1)

## 参考资料

- 官网: https://github.com/dbohdan/sqawk