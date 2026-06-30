# php85-pecl-memcache 2.3.3 适配笔记

## 编译环境
- 构建系统: autotools (phpize + configure)
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- 状态: published

## 编译步骤

使用 phpize + configure + make 编译 PHP 扩展：
```bash
phpize
./configure --prefix=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | 缺少 ohos 平台检测 | 添加 HarmonyOS/__OHOS__ case |
| 2 | config.sub 不支持 ohos-linux | OS 识别列表缺少 ohos | 添加 ohos-linux 三元组 |
| 3 | smart_string.h 宏缺失 | PHP 8.5 移除 smart_string | 使用 zend_string 替代宏 |
| 4 | config.h 需要平台宏 | 缺少 __OHOS__ 定义 | 添加 #define __OHOS__ 1 |

## 交付物

| 文件 | 说明 |
|------|------|
| php85-pecl-memcache-2.3.3-ohos-aarch64.tar.gz | 预编译包 |
| php85-pecl-memcache-2.3.3-ohos-aarch64-debug.tar.gz | debug 预编译包 |
