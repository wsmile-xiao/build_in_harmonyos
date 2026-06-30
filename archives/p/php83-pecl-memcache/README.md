# PHP 8.3 PECL Memcache

> PHP memcache extension for PHP 8.3 caching via memcached servers

## 简介

php83-pecl-memcache 是 PHP 8.3 的 memcache 扩展，提供通过 memcached/memcache 服务器的数据缓存功能。支持连接池、一致性哈希、二进制协议等特性。

## OHOS 适配要点

- config.h.in 和 configure.ac 需添加 __OHOS__ 条件宏
- memcache 源码文件需要 zend_string/reallocarray 适配
- Makefile.objects 需修改以适配 OHOS 编译流程
- memcache_pool.h 需要 reallocarray extern 声明

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| php83 | 8.3 | PHP 运行时 |

## 参考

- [PECL Memcache](https://pecl.php.net/package/memcache)
