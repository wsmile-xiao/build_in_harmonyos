# TXR

TXR是一个强大的文本处理和数据提取语言，结合了模式匹配、数据处理和脚本编程功能。

## 基本信息

- **名称**: txr
- **版本**: 302
- **类别**: text-processing
- **网站**: https://kylheku.com/txr/

## OHOS 编译信息

- **编译日期**: 2026-05-26
- **构建系统**: configure
- **编译器**: clang
- **状态**: built
- **预编译包**: txr-302-ohos-aarch64.tar.gz (6.1M)

## 功能特性

TXR提供了：
- 强大的文本模式匹配
- 数据提取和转换
- Lisp-like编程语言
- 标准库支持
- 多种数据处理工具

## 依赖

- libffi 3.4.6 (用于FFI支持)

## 编译要点

### OHOS平台适配
1. 需要设置CC环境变量为clang
2. 使用预编译libffi 3.4.6包
3. 手动添加libffi编译选项
4. txr不支持DESTDIR，需要手动创建打包结构

### 配置参数
```bash
export CC=clang
export CXX=clang++
./configure --prefix=/storage/Users/currentUser/usr/local
make -j2
make install
```

## 验证

```bash
txr --version
# 输出: version 302
```

## 预编译包内容

```
txr-302-ohos-aarch64.tar.gz:
- bin/txr (主程序)
- share/txr/stdlib/ (标准库)
```

## 注意事项

- txr版本号使用简单数字格式（如"302"）
- 需要libffi预编译包支持
- ELF签名已完成（鸿蒙平台必须）