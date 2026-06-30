# PHP 8.4 PECL MongoDB

> PHP MongoDB driver extension for PHP 8.4

## 简介

php84-pecl-mongodb 是 PHP 8.4 的 MongoDB 驱动扩展，提供与 MongoDB 数据库的连接和操作功能。支持连接池、事务、Change Stream 等现代 MongoDB 特性。

## OHOS 适配要点

- 使用 phpize + configure + make 标准编译流程，无需源码修改
- 需要安装 php84 和 mongodb 相关依赖

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| php84 | 8.4 | PHP 运行时 |

## 功能验证

```bash
php -m | grep mongodb
```

## 参考

- [MongoDB PHP Driver](https://www.mongodb.com/docs/drivers/php/)
- [GitHub: mongodb/mongo-php-driver](https://github.com/mongodb/mongo-php-driver)
