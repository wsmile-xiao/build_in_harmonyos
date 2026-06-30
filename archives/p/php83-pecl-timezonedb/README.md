# PHP 8.3 PECL TimezoneDB

> PHP timezonedb extension providing updated timezone data

## 简介

php83-pecl-timezonedb 是 PHP 8.3 的时区数据库扩展，提供更新的时区数据（比 PHP 内置数据更及时），确保时间相关功能的准确性。

## OHOS 适配要点

- build/config.guess 需添加 HarmonyOS 平台检测分支
- config.h 需添加 __OHOS__ 定义
- 使用 phpize + configure + make 标准编译流程

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| php83 | 8.3 | PHP 运行时 |

## 功能验证

```bash
php -m | grep timezonedb
```

## 参考

- [PECL TimezoneDB](https://pecl.php.net/package/timezonedb)
