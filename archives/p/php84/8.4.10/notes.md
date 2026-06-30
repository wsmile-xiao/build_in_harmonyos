# PHP 8.4.10 编译笔记

## 编译日期
2026-05-27 14:25:02

## 平台信息
- 系统: HarmonyOS
- 架构: aarch64
- 编译器: clang

## 关键问题及解决方案

### 1. config.guess 无法识别 HarmonyOS (E007)
**问题**: GNU config.guess 脚本不包含 HarmonyOS 检测分支
**解决方案**: 使用 patch-autotools-ohos.pl 补丁脚本修复 build/config.guess 和 build/config.sub

### 2. config.status 临时目录权限问题
**问题**: config.status 使用硬编码的 ./confXXXXXX 临时目录，在当前目录无法创建
**解决方案**: 修改 config.status 第 605-612 行，将临时目录改为固定路径 /storage/Users/currentUser/tmp/php84-build-tmp

### 3. pthread_setcanceltype/pthread_cancel 未实现
**问题**: HarmonyOS 不支持 pthread_setcanceltype 和 pthread_cancel 函数
**影响**: phpdbg 模块无法编译
**解决方案**: 使用 --disable-phpdbg 禁用 phpdbg，只编译必需的 CLI 模块

## 编译选项
```bash
./configure --prefix=/storage/Users/currentUser/usr/local \
  --disable-all \
  --enable-cli \
  --disable-phpdbg
```

## 编译产物
- php CLI: 19MB
- php-cgi: 19MB (可选，未测试)

## 验证结果
```bash
$ ~/usr/local/bin/php --version
PHP 8.4.10 (cli) (built: May 27 2026 14:25:02) (NTS)
Copyright (c) The PHP Group
Zend Engine v4.4.10, Copyright (c) Zend Technologies
```

## 知识提取
- E007 补丁适用于所有 PHP 版本的 autotools 文件
- config.status 临时目录修复适用于所有 GNU autoconf 项目
- HarmonyOS 缺少 pthread_setcanceltype/pthread_cancel，影响需要线程取消功能的软件
