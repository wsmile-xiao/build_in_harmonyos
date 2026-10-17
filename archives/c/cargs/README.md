# cargs

A simple argument parser library for C.

## 简介

cargs 是一个轻量级的命令行参数解析库，用于 C 语言项目。它提供了简单易用的 API 来处理命令行选项，支持长选项、短选项、选项值等常用功能。

## 官方链接

- 官方网站: https://likle.github.io/cargs/
- 代码仓库: https://github.com/likle/cargs
- 许可证: MIT

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.2.0 | published | 首次适配 |

## 使用方式

在 Conan 项目中添加依赖：

```python
def requirements(self):
    self.requires("cargs/1.2.0")
```

## 适配说明

- 构建系统: CMake
- 测试: 23 个单元测试（20/23 通过，3 个因鸿蒙系统 /tmp 只读失败）
- 依赖: 无外部依赖
