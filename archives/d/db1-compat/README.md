# db1-compat

db1-compat 提供源自 4.4BSD DB 1.85 的嵌入式键值数据库兼容接口。

## 功能概述

- 提供 B-tree、Hash 和 Recno 三种访问方法。
- 提供传统 `dbopen` 接口及 NDBM 兼容接口。
- 提供页面缓存（mpool）公共接口。

## OHOS 适配

源码原本作为 glibc 子目录构建。本归档增加独立 CMake 构建入口，并为 OHOS
musl 的 `sys/queue.h` 补充 DB 1.85 所需的旧式 `CIRCLEQ` 宏。补丁为通用
libc 可移植性修改，不依赖平台专有桩代码。

## 依赖关系

仅依赖 C 标准库及 POSIX 文件接口，无第三方构建或运行依赖。

## 参考资料

- https://www.gnu.org/software/libc/
- https://ftp.gnu.org/gnu/glibc/glibc-2.1.3.tar.gz
