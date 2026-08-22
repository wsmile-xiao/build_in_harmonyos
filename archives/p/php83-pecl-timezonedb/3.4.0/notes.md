# php83-pecl-timezonedb 3.4.0 适配笔记

## 编译环境
- 构建系统: 直接编译 (clang + PHP headers)
- 编译日期: 2026-08-22
- 编译器: clang/clang++
- 状态: published

## 源码信息
- 上游版本: timezonedb 2025.2 (日期命名)
- 内部版本号: 3.4.0 (OHPC 映射)
- 源码地址: https://pecl.php.net/get/timezonedb-2025.2.tgz

## 编译步骤

1. 安装 PHP 开发包: `conan install --requires=php/8.5.8`
2. 应用 config.h 补丁
3. 直接编译 timezonedb.c:
   ```
   clang -fPIC -shared -O2 -Wall \
     -DCOMPILE_DL_TIMEZONEDB -DHAVE_CONFIG_H \
     -I<php_pkg>/include/php -I<php_pkg>/include/php/main \
     -I<php_pkg>/include/php/Zend -I<php_pkg>/include/php/TSRM \
     -I<php_pkg>/include/php/ext/date/lib \
     -o timezonedb.so timezonedb.c
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | phpize 无法找到 build files | php-config/phpize 硬编码 prefix='/'，conan 隔离环境下路径不匹配 | 改为直接编译，不使用 phpize |
| 2 | TIMELIB_SUPPORTS_V2DATA 未定义 | timezonedb.h 要求此宏，PHP 8.5 已内置支持但头文件未导出 | 直接编译时 timezonedb.c 内部已定义 |
| 3 | 上游 URL 404 | manifest 中的 URL 使用了错误版本号 3.4.0，实际上游版本为 2025.2 | 修正 URL 为 timezonedb-2025.2.tgz |
| 4 | config.h 缺少平台宏 | 缺少 __OHOS__ 定义 | 使用 0002-config.h.patch 创建 config.h |

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| php | 8.5.8 | PHP 运行时和开发头文件 (注册仓中最新版) |

## 交付物

| 文件 | 说明 |
|------|------|
| timezonedb.so | PHP 时区数据库扩展 (ELF 64-bit arm64) |

## 结束
status: COMPLETED
