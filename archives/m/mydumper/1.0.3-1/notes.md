# mydumper 1.0.3-1 适配笔记

## 任务背景

- 平台任务 contrib-5764（依赖活动，calbee21 认领）
- main 归档已有 mydumper/1.0.3（#2721，wujiayang1，stub-mysql 路线）
- 本版 1.0.3-1 = **真实 mariadb-connector-c/3.4.8 链接**，与 1.0.3 并存
  （带连字符版本号先例：ad2vcf/0.1.6-19、busted/2.2.0-1）

## 依赖决策

| 依赖 | 版本 | 决策依据 |
|---|---|---|
| glib2 | 2.88.0.1 | 制品仓已发布，R35 实测二进制可下载 |
| pcre2 | 10.45 | **源码实际用 PCRE2 API**（pcre2.h/pcre2_compile、CMake find_package(PCRE2)）；任务参数 pcre/8.45 为 PCRE1 技术上不可行；与 glib2/2.88.0.1 依赖链一致 |
| zlib | 1.3.1 | 与 glib2 链一致 |
| mariadb-connector-c | 3.4.8 | 真实 MySQL 客户端（R35 实测二进制可下载），include/mariadb/{mysql.h...} + lib/mariadb/libmariadb.so |

## 关键技术点

1. **MYSQL_OPT_SSL_MODE（MariaDB 兼容）**：connection.c:250 的该调用在
   `#else`（非 LIBMARIADB）分支，使用 MySQL 8 专有枚举（SSL_MODE_DISABLED/
   PREFERRED/VERIFY_IDENTITY 等），MariaDB 头无此枚举。解法：CFLAGS 传
   `-DLIBMARIADB` 走 `#ifdef LIBMARIADB` 分支（MYSQL_OPT_SSL_ENFORCE /
   MYSQL_OPT_SSL_VERIFY_SERVER_CERT，MariaDB 专有选项）——无需 patch。

2. **FindMySQL.cmake 交叉环境探测失败**：靠 mariadb_config/mysql_config
   程序（OHOS 无）→ 配方预置 MYSQL_INCLUDE_DIR/MYSQL_LIBRARIES/
   MYSQL_CFLAGS 指向 mariadb-connector-c 包布局（include/mariadb、
   lib/mariadb/libmariadb.so）。

3. **FindGLIB2/FindPCRE2 同理**：0002-glib2-find.patch（先例复用）+ 预置
   PCRE2_INCLUDE_DIR/PCRE2_LIBRARY（8 位变体 pcre2-8）。

4. **make -j1**：OHOS 禁 mkfifo jobserver（catdoc/ccze/openvdb 同款）。

5. **CMAKE_POLICY_VERSION_MINIMUM=3.5**：上游 CMakeLists 用较新策略版本。

## 上游测试

上游无 CMake 测试注册（tests/ 需真实 MySQL server，OHOS 目标环境不适用）
→ test_package 脚本验证二进制可执行 + mydumper --version 实际运行
（先例 1.0.3 同款）。
