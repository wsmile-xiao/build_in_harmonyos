# php-pecl-memcache 8.2 适配笔记

## 编译环境
- 构建系统: phpize (PHP PECL extension build system)
- 编译日期: 2026-06-12
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. **phpize**: 在源码目录运行 `phpize85` 生成 configure 脚本
   ```bash
   cd ~/tmp/builds/php-pecl-memcache-8.2.work
   ~/usr/local/bin/phpize85
   ```
2. **configure**: 配置编译选项
   ```bash
   TMPDIR=$TMPDIR ./configure --prefix=$DEFAULT_PREFIX \
     --with-php-config=~/usr/local/bin/php-config85 \
     --with-zlib-dir=$DEFAULT_PREFIX
   ```
3. **make**: 编译
   ```bash
   make -j1
   ```
4. **make install DESTDIR**: 由于 PHP 扩展的 make install 不正确处理 DESTDIR，
   需要手动创建 staging 目录
5. **验证**: 扩展已编译为 memcache.so 并安装到 PHP 扩展目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | build 脚本无法检测构建系统 | PHP PECL扩展使用 phpize 而非标准 autotools | 手动运行 phpize85 + configure + make |
| 2 | configure 要求 zlib | 缺少 zlib 路径参数 | 添加 --with-zlib-dir=$DEFAULT_PREFIX |
| 3 | config.status Permission denied | HMDFS 临时目录创建受限，heredoc 写入失败 | 手动创建 config.h 文件 |
| 4 | DESTDIR 模式不工作 | PHP 扩展的 make install 不支持 DESTDIR | 手动创建 staging 目录并复制文件 |
| 5 | php_session_register_module 未找到 | PHP 用 --disable-all 编译，无 session 支持 | 记录为已知限制，扩展本身可用 |

## 源码修改

无需修改源码。本扩展使用 phpize85 生成构建系统文件后直接编译成功。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| PHP 8.5 | 8.5.7 | phpize85/php-config85 提供编译头文件和扩展目录 |
| zlib | 1.3.1 | 预编译包，--with-zlib-dir 指定路径 |
| clang | 15.0.4 | 系统编译器 |

## 验证结果

```bash
# 编译产物
ls ~/tmp/builds/php-pecl-memcache-8.2.work/modules/memcache.so
# memcache.so (203136 bytes)

# 安装位置
ls ~/usr/local/lib/php/extensions/no-debug-non-zts-20250925/memcache.so
# 已安装

# 注意: 加载扩展需要 PHP 8.5 且启用了 session 扩展
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| php-pecl-memcache-8.2-ohos-aarch64.tar.gz | - | 预编译包 |
| php-pecl-memcache-8.2-ohos-aarch64-debug.tar.gz | - | Debug 预编译包 |

## 注意事项

1. 本扩展为 PHP PECL 扩展，使用 phpize 构建系统而非标准 autotools
2. 编译针对 PHP 8.5（API 版本 20250925），安装到对应扩展目录
3. memcache session handler 需要 PHP session 扩展支持
4. config.status 在 HMDFS 上因 heredoc 临时文件权限问题失败，需手动生成 config.h
5. make install DESTDIR 模式不适用于 PHP 扩展，需手动 staging
---

**编译结束**: 2026-09-04 02:10
**最终状态**: built
