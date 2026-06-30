# Nickle

**版本**: 2.108  
**构建系统**: Meson  
**许可证**: BSD  

## 简介

Nickle是一个编程语言和计算环境，支持无限精度整数和分数、数组、结构体等数据类型。它提供了强大的数学计算能力，适合科学计算和脚本编程。

## 功能特性

- 无限精度整数和分数运算
- 数组、结构体、联合体等复合数据类型
- Readline支持（交互式命令行编辑）
- POSIX线程支持
- Socket编程支持
- 丰富的内置数学函数库

## 预编译包

- `nickle-2.108-ohos-aarch64.tar.gz` - HarmonyOS aarch64预编译包

## 补丁说明

### 0001-meson.build.patch
修复C标准问题：将`gnu23`改为`gnu2x`，适配当前编译器支持的C标准范围。

### 0002-bench-meson.build.patch  
修改GMP依赖查找方式：使用`dependency('gmp')`替代`cc.find_library('gmp')`，确保通过pkg-config正确找到GMP库。

### 0003-.pre-scan-report.yaml.patch
预编译风险扫描报告，记录了构建工具和依赖的可用性检查结果。

## 依赖

- GMP 6.3.0（无限精度数学库）
- Readline 8.2（命令行编辑）
- ncurses（Readline依赖）

## 编译参数

```bash
meson setup builddir --prefix=/storage/Users/currentUser/usr/local
ninja -C builddir
ninja -C builddir install
```

## 遇到的问题

1. **C标准不支持**: meson.build中设置的`c_std=gnu23`超出编译器支持范围，修改为`gnu2x`。
2. **GMP库查找失败**: bench/meson.build使用`cc.find_library('gmp')`无法通过pkg-config找到库，改为`dependency('gmp')`。
3. **Readline.pc路径错误**: readline.pc文件包含错误的临时路径，修复为正确的安装路径。

## 知识提取

- E097: Meson C标准适配（gnu23 → gnu2x）
- E098: Meson依赖查找方式（find_library → dependency）

