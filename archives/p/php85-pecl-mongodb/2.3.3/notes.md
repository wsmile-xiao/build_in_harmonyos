# php85-pecl-mongodb 2.3.3 — 适配笔记

## 编译信息
- **版本**: 2.3.3
- **构建系统**: autotools (phpize + configure + make)
- **编译器**: clang / clang++
- **状态**: built

## 编译流程

1. **PHP 8.5.7 开发环境准备**: 从PHP源码configure生成php_config.h和phpize/php-config脚本，安装开发头文件到~/usr/local/include/php/
2. **phpize**: 使用phpize85在mongodb源码目录生成configure脚本
3. **configure**: `--enable-mongodb --with-php-config=php-config85 --with-mongodb-client-side-encryption=no --build=aarch64-unknown-linux-gnu`
4. **make**: 编译成功，生成mongodb.so (2.2MB)
5. **make install INSTALL_ROOT=$TEST_PREFIX**: staging安装

## 遇到的问题及解决

### 问题1: PHP 8.5 configure config.status失败
- **现象**: `./config.status[881]: can't create ./confXXXXXX/subs1.awk: Permission denied`
- **原因**: HarmonyOS文件系统setgid位导致新目录权限drwx--S---，非owner用户无法写入
- **解决**: sed移除config.status中的`umask 077`，改为不带umask的mktemp/mkdir

### 问题2: config.guess无法识别HarmonyOS
- **现象**: config.guess输出unknown系统
- **解决**: 替换为支持HarmonyOS的config.guess/config.sub版本

### 问题3: PHP开发头文件缺失
- **现象**: 编译mongodb时找不到streams/php_stream_context.h等头文件
- **解决**: 从PHP源码树安装所有开发头文件到~/usr/local/include/php/

### 问题4: DESTDIR安装
- **现象**: PHP扩展Makefile使用INSTALL_ROOT而非DESTDIR
- **解决**: 使用`INSTALL_ROOT=$TEST_PREFIX make install`

### 问题5: conftest.c创建失败(PHP configure)
- **现象**: PHP configure的标准头文件检测全部失败(conftest.c无法创建)
- **解决**: 设置TMPDIR到~/tmp/php-tmp可写目录

## 捆绑库信息
- libmongoc: Bundled (2.3.0)
- libbson: Bundled (2.3.0)
- libmongocrypt: None (client-side encryption disabled)
- OpenSSL: System (3.5.6)
- utf8proc: Bundled (2.8.0)
- zlib: Bundled (1.3.1)
- kms-message: Bundled---

**编译结束**: 2026-06-09 11:56
**最终状态**: built
---

**编译结束**: 2026-06-09 12:03
**最终状态**: built
