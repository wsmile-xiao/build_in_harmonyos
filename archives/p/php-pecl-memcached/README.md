# PHP PECL Memcached

> PHP memcached extension using libmemcached library

## 简介

php-pecl-memcached 是 PHP 的 memcached 扩展，基于 libmemcached 库提供高性能的 memcached 缓存操作。支持多服务器、一致性哈希、二进制协议、CAS 操作等。

## OHOS 适配要点

- build/config.guess 和 config.sub 需添加 HarmonyOS 平台检测分支
- 使用 phpize + configure + make 标准编译流程

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| php | 8.x | PHP 运行时 |
| libmemcached | 1.x | memcached C 客户端库 |

## 参考

- [GitHub: php-memcached-dev/php-memcached](https://github.com/php-memcached-dev/php-memcached)
