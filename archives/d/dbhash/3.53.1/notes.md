# dbhash 3.53.1 编译笔记

## 编译日期
2026-05-21

## 背景
dbhash 是 SQLite 源码树中的一个工具程序（tool/dbhash.c），用于计算 SQLite 数据库内容的一致性哈希。

## 源码获取
- URL: https://www.sqlite.org/2026/sqlite-src-3530100.zip
- 版本: SQLite 3.53.1
- 大小: 13.84 MiB

**注意**: SQLite 官网 SSL 连接不稳定，下载速度较慢（约 1M/min）。

## 平台适配

### 问题 1: config.guess 无法识别 HarmonyOS

SQLite 源码使用 autosetup 构建系统，其 autosetup/autosetup-config.guess 文件不包含 HarmonyOS 识别规则。

**解决方案**:
使用 libtool 已适配的 config.guess 和 config.sub 替换：
```
cp libtool/config.guess autosetup/autosetup-config.guess
cp libtool/config.sub autosetup/autosetup-config.sub
```

### 问题 2: autosetup 编译器检测失败

autosetup 的编译器检测脚本无法正确检测 HarmonyOS 上的 clang 编译器。

**解决方案**:
放弃 autosetup，采用手动编译方式：
1. 使用 sqlite-autoconf 版本的 amalgamation（sqlite3.c/sqlite3.h）
2. 从完整源码复制 dbhash.c
3. 手动编译并链接

### 问题 3: TMPDIR 权限

HarmonyOS 默认 /tmp 目录只读，autosetup 需要创建临时文件。

**解决方案**:
设置 TMPDIR 环境变量：
```
export TMPDIR=$HOME/tmp
```

## 编译步骤

### 1. 编译 SQLite amalgamation
```bash
clang -c -fPIC -O2 -DSQLITE_ENABLE_FTS5 sqlite3.c -o sqlite3.o
ar rcs sqlite3.a sqlite3.o
```

### 2. 编译 dbhash
```bash
cp sqlite-src-*/tool/dbhash.c .
clang -c -fPIC -O2 -I. dbhash.c -o dbhash.o
clang dbhash.o sqlite3.a -o dbhash -lpthread -ldl -lm
```

## 验证
```bash
./dbhash --help
```

## 编译产物
- dbhash: 1.3 MiB 静态可执行文件（SQLite 嵌入）

## 注意事项
1. dbhash 依赖 sqlite3.h，需要使用 amalgamation 版本的头文件
2. 需要链接 pthread、dl、m 库
3. 推荐启用 SQLITE_ENABLE_FTS5 等常用扩展