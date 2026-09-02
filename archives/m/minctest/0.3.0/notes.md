# minctest 0.3.0 编译笔记

## 软件信息

- **名称**: minctest
- **版本**: 0.3.0
- **类型**: header-only library
- **许可证**: Zlib
- **官网**: https://codeplea.com/minctest
- **源码**: https://github.com/codeplea/minctest

## 编译概要

minctest 是一个极简的 C 语言单元测试框架，仅包含一个头文件 `minctest.h`，无需编译。

### 构建系统

无（header-only）

### 依赖项

无

## 适配过程

### 1. 源码获取

从 GitHub master 分支下载：
- URL: https://github.com/codeplea/minctest/archive/refs/heads/master.tar.gz
- SHA256: a86511626dc04e7163982b51d5b2a787fe0285d13aba1fc15cc4faa1f1d786fe

### 2. Conan 配方

创建 header-only 类型的 conanfile.py：
- `package_type = "header-library"`
- `build()` 为空方法
- `package()` 仅复制头文件和许可证

### 3. 测试验证

使用上游 example.c 的测试代码验证所有 API：
- `lok()` - 布尔断言
- `lequal()` - 整数相等
- `lfequal()` - 浮点数相等
- `lsequal()` - 字符串相等

所有测试通过。

## 知识沉淀

1. minctest 是纯头文件库，无需编译
2. 上游提供完整测试示例 example.c
3. 所有 API 在鸿蒙平台正常工作

## 编译完成

✅ 适配完成，配方已验证通过。

## 结束标记

**最终状态**: published  
**编译日期**: 2026-08-31
