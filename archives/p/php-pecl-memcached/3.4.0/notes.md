# php-pecl-memcached 3.4.0 适配笔记

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
| 1 | config.guess 不识别 HarmonyOS | 缺少 ohos 平台检测 | 添加 HarmonyOS/__OHOS__ case |
| 2 | config.sub 不支持 ohos-linux | OS 识别列表缺少 ohos | 添加 ohos-linux 三元组 |

## 交付物

| 文件 | 说明 |
|------|------|
| php-pecl-memcached-3.4.0-ohos-aarch64.tar.gz | 预编译包 |
| php-pecl-memcached-3.4.0-ohos-aarch64-debug.tar.gz | debug 预编译包 |
