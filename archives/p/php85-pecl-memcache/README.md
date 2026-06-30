# PHP 8.5 PECL Memcache

> PHP memcache extension for caching via memcached servers

## 简介

php85-pecl-memcache 是 PHP 8.5 的 memcache 扩展，提供通过 memcached/memcache 服务器的数据缓存功能。支持连接池、一致性哈希、二进制协议等特性。

## OHOS 适配要点

- build/config.guess 和 config.sub 需添加 HarmonyOS 平台检测分支
- PHP smart_string 宏在 OHOS 上需要 zend_string 替代宏定义
- 使用 phpize + configure + make 标准编译流程

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| php85 | 8.5 | PHP 运行时 |

## 功能验证

```bash
php -m | grep memcache
```

## 参考

- [PECL Memcache](https://pecl.php.net/package/memcache)
