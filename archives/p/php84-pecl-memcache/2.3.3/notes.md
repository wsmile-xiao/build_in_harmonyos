# php84-pecl-memcache 2.3.3 适配笔记

## 编译环境
- 构建系统: phpize + autotools (configure + make)
- 编译日期: 2026-08-22
- 编译器: clang/clang++
- 状态: built

## 源码
- 源码: PECL memcache 8.2 (https://pecl.php.net/get/memcache-8.2.tgz)
- SHA256: b3f0640eacdeb9046c6c86a1546d7fb8a4e9f219e5d9a36a287e59b2dd8208e5
- 版本说明: 包名 php84-pecl-memcache，版本 2.3.3，实际源码为 PECL memcache 8.2

## 依赖
- php/8.5.8 (PHP 运行时，提供 phpize、php-config 和开发头文件)
- zlib/1.3.1 (压缩库)

## 适配修改

### 1. smart_string 头文件路径修复 (0001-fix-smart-string-includes.patch)
PHP 8.5 将 smart_string 头文件从 `ext/standard/` 移动到 `Zend/` 目录：
- `ext/standard/php_smart_string.h` → `zend_smart_string.h`
- `ext/standard/php_smart_string_public.h` → `zend_smart_string_public.h`

涉及文件：memcache_pool.h, memcache_pool.c, memcache_session.c, memcache_ascii_protocol.c, memcache_binary_protocol.c

### 2. phpize prefix 修复
conan 安装的 PHP 使用 `prefix='/'`，phpize 的 `phpize_replace_prefix()` 函数使用 sed 替换所有 `/` 为 prefix，
当 prefix 包含 `/` 时会导致 m4_include 路径损坏。修复方法：直接 `cp phpize.m4 configure.ac`。

### 3. config.status umask 修复
HarmonyOS HMDFS 文件系统中，`umask 077` 创建的目录权限为 `drwx--S---`，
系统拒绝在此目录中写入文件。修复方法：将 `umask 077` 替换为 `umask 000`。

### 4. Session 支持禁用
PHP conan 包使用 `--disable-all` 编译，未安装 session 扩展头文件。
使用 `--disable-memcache-session` 禁用 memcache 的 session 支持。
这是构建时选项，不是源码裁剪。memcache 缓存功能完整保留。

### 5. zlib -fPIC 问题
zlib conan 包为静态库（libz.a），未使用 -fPIC 编译。
链接到 PHP 共享扩展（memcache.so）时需要 -fPIC 编译的 zlib。
conanfile.py 中通过 conan 的 shared 选项或构建时处理。

## 编译步骤
1. 下载源码并解压
2. 应用补丁（smart_string 路径修复）
3. 运行 phpize 生成 configure 脚本
4. 运行 ./configure --with-php-config --with-zlib-dir --disable-memcache-session
5. 修复 config.status umask 问题
6. 运行 make 生成 memcache.so

## 交付物
| 文件 | 说明 |
|------|------|
| memcache.so | PHP memcache 扩展共享库 |
---

**编译结束**: 2026-08-22 08:42
**最终状态**: built

## 最终状态
COMPLETED: Conan recipe created, conan-verify passed, W3 CI passed, W4 audit passed, ready for PR.

## 提交
PR submission: 2026-08-22T01:02:21Z
