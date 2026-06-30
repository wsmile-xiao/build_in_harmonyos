# php83 8.3.30 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: **success** ✅

## 编译过程与解决方案

### 问题一：config.guess 无法识别 HarmonyOS 平台（E007）

**根因分析**：
GNU autotools 的 config.guess 脚本不支持 OpenHarmony/HarmonyOS 平台识别。

**解决方案**：
应用 `patch-autotools-ohos.pl` 补丁到 `build/config.guess`，添加 HarmonyOS 检测分支。

### 问题二：config.sub 拒绝 linux-ohos 组合

**根因分析**：
config.sub 第 1787 行附近的内核-OS 组合验证列表不包含 `linux-ohos*`。

**解决方案**：
在 config.sub 中添加 `linux-ohos*` 到内核验证列表：
```bash
# 在第 1787 行附近添加：
linux-ohos*)
    ;;
```

### 问题三：config.status 临时目录创建失败（核心问题）

**根因分析**：
config.status 脚本使用硬编码的 `./confXXXXXX` 模式创建临时目录，**不使用 TMPDIR 环境变量**。

关键代码位置（config.status 第 632 行附近）：
```bash
tmp=./conf$$-$$
# 或类似模式，不以 $TMPDIR 开头
```

**解决方案**：
修改 config.status 第 632 行，将临时目录硬编码为固定路径：
```bash
tmp=/storage/Users/currentUser/tmp/php83-build-tmp
mkdir -p "$tmp"  # 确保目录存在
```

### 问题四：zend_vm_gen.php 运行失败

**根因分析**：
PHP 构建过程需要运行 `Zend/zend_vm_gen.php` 来生成虚拟机执行代码，但当前系统的 PHP 可能缺少 `file()` 函数支持。

**解决方案**：
使用之前编译的 PHP 8.2.28 运行 zend_vm_gen.php：
```bash
~/builds/php-8.2.28.work/sapi/cli/php Zend/zend_vm_gen.php
```

### 问题五：phpdbg 链接失败

**根因分析**：
phpdbg_watch.c 使用 `pthread_setcanceltype` 和 `pthread_cancel` 函数，但链接时未正确包含 pthread 库。

**解决方案**：
跳过 phpdbg 构建，只安装 cli 和 cgi 二进制文件：
```bash
make install-cli install-cgi install-build install-headers install-programs
```

## 所有问题汇总

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别平台 | 缺少 HarmonyOS 检测分支 | 应用 E007 补丁 |
| 2 | config.sub 拒绝 linux-ohos | 内核-OS 组合验证缺失 | 手动添加 linux-ohos* |
| 3 | config.status 临时目录失败 | 不使用 TMPDIR，硬编码 ./confXXXXXX | 硬编码为固定目录 |
| 4 | zend_vm_gen.php 失败 | 需要已有 PHP 运行 | 使用 PHP 8.2.28 |
| 5 | phpdbg 链接失败 | pthread 函数未链接 | 跳过 phpdbg |
| 6 | 缺少 C 编译器 | 系统无 cc 命令 | 设置 CC=clang |
| 7 | 缺少 re2c | 构建工具缺失 | 安装预编译包 |

## 验证结果

```bash
$ php --version
PHP 8.3.30 (cli) (built: May 27 2026 11:17:21) (NTS)
Copyright (c) The PHP Group
Zend Engine v4.3.30, Copyright (c) Zend Technologies

$ php -r 'echo "Hello, HarmonyOS!\n";'
Hello, HarmonyOS!

$ php -r 'phpinfo();' | grep System
System => HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP Wed Apr 29 10:16:03 UTC 2026 aarch64
```

## 关键知识点

1. **GNU autoconf 不使用 TMPDIR**：config.status 的临时目录创建使用硬编码的 `./confXXXXXX` 模式，需要手动修改。

2. **HarmonyOS 平台三元组**：`aarch64-unknown-linux-ohos`

3. **PHP 自举问题**：编译 PHP 需要 PHP 来运行 zend_vm_gen.php，需要先有一个可用的 PHP 版本。

## 预编译包位置

- 打包目录：`archives/p/php83/8.3.30/packaging/pkg-php83-8.3.30/`
- 安装前缀：`/storage/Users/currentUser/usr/local`
- 主要文件：
  - `bin/php` - PHP CLI
  - `bin/php-cgi` - PHP CGI
  - `bin/php-config` - 配置信息
  - `bin/phpize` - 扩展构建工具
