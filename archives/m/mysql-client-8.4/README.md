# mysql-client-8.4

MySQL 8.4 LTS 客户端库与客户端工具（HarmonyOS PC / OHOS aarch64 适配）。

ConanCenter libmysqlclient 风格的纯客户端包：`libmysqlclient.a` 静态客户端库 + `mysql`、`mysqladmin`、`mysqldump`、`mysqlbinlog`、`mysql_config` 等客户端命令行工具。不含服务器组件（WITHOUT_SERVER=ON）。

与仓库既有 `mysql/8.0.46`（8.0 系列服务器同源完整包）为同源不同包名并存。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 8.4.11 | published | MySQL 8.4 LTS 最新 GA，client-only 构建 |

## 依赖

- openssl/3.5.6.1.1
- zlib/1.3.1
- ncurses/6.4

## 使用

```cmake
find_package(mysqlclient REQUIRED)
target_link_libraries(myapp PRIVATE mysqlclient::mysqlclient)
```

```bash
conan install --requires=mysql-client-8.4/8.4.11
```
