# argh

## 概述
argh 是一个 C++11 极简命令行参数处理器，采用 header-only（单文件）设计，只需包含 `argh.h` 即可使用。

## 特性
- **Header-only**: 只有一个 `argh.h` 头文件，无需链接库
- **零依赖**: 不依赖任何外部库
- **C++11 标准**: 兼容 C++11 及以上版本
- **支持三种参数类型**:
  - Positional args (位置参数)
  - Flags (布尔标志)
  - Parameters (带值的命名参数)

## 上游仓库
- GitHub: https://github.com/adishavit/argh
- License: BSD-3-Clause

## 构建系统
- CMake (INTERFACE library)

## 适配版本
| 版本 | 状态 | 构建系统 |
|------|------|---------|
| 1.3.2 | built | CMake |
