# php83-pecl-memcache 2.3.3 适配笔记

## 编译环境
- 构建系统: autotools (phpize + configure)
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- 状态: published

## 编译步骤

使用 phpize + configure + make 编译 PHP 扩展。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.h.in 缺少平台宏 | 缺少 __OHOS__ 守卫条件 | 添加 #ifdef __OHOS__ 条件宏 |
| 2 | configure.ac 缺少平台检测 | 缺少 OHOS 平台条件 | 添加 __OHOS__ AC_DEFINE |
| 3 | reallocarray 未声明 | musl libc 缺少声明 | 在 memcache_pool.h 添加 extern 声明 |
| 4 | memcache 源码兼容性 | PHP 8.3 API 变化 | 适配 zend_string 和新 API |

## 交付物

| 文件 | 说明 |
|------|------|
| php83-pecl-memcache-2.3.3-ohos-aarch64.tar.gz | 预编译包 |
| php83-pecl-memcache-2.3.3-ohos-aarch64-debug.tar.gz | debug 预编译包 |
