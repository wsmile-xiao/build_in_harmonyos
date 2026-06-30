# libpcre16

## 简介

PCRE (Perl Compatible Regular Expressions) 是一个实现 Perl 风格正则表达式的库。libpcre16 是 PCRE 的 16 位字符版本，支持 UTF-16 编码。

## 功能概述

- Perl 风格正则表达式匹配
- 16 位字符支持（UTF-16）
- 32 位字符支持（UTF-32）
- POSIX 兼容接口
- C++ 封装库
- 提供 pcregrep 和 pcretest 工具

## OHOS 适配要点

1. **平台识别**：应用 config.guess/config.sub 补丁添加 HarmonyOS 检测
2. **umask 适配**：configure 中 `umask 077` 改为 `umask 022` 解决 HMDFS 权限问题
3. **编译选项**：使用 `--enable-pcre16 --enable-pcre32` 启用 16/32 位支持
4. **测试通过**：make check 5/5 PASS

## 依赖关系

- **编译依赖**：无外部依赖
- **运行依赖**：无外部依赖

## 参考资料

- 官网：https://www.pcre.org
- 源码：https://sourceforge.net/projects/pcre