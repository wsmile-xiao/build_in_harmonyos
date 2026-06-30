# PostGIS

## 简介
PostGIS 是 PostgreSQL 的空间数据库扩展器，添加了对地理对象的存储、索引和查询支持。

## OHOS 适配
- **核心问题**：GEOS 静态库链接需要显式添加 `-lgeos -lc++`
- **libiconv 链接**：需要使用 `--with-libiconv-prefix` 参数指定 libiconv 路径
- **PostgreSQL 依赖**：需要完整的 PostgreSQL 安装（包括 pg_config 和 PGXS）
- **编译系统**：autotools

## 依赖
- PostgreSQL 17.2+
- GEOS 3.13.0+
- PROJ 9.8.1+
- libxml2 2.11.9+
- libiconv 1.17+

## 功能验证
编译产物：
- shp2pgsql：Shapefile 导入工具
- pgsql2shp：PostgreSQL 导出工具
- postgis-3.so：PostGIS 共享库

## 参考
- 官网：https://postgis.net
- 源码：https://github.com/postgis/postgis