# UTF8CPP

> UTF-8 with C++ in a Portable Way

## 简介

UTF8CPP (utfcpp) 是一个轻量级的 C++ UTF-8 字符串处理库，提供简洁优雅的接口用于 UTF-8 编码/解码、验证和迭代。它是一个 header-only 库，只需包含头文件即可使用，无需编译链接。

该库广泛应用于需要处理 UTF-8 文本的 C++ 项目中，特别是在跨平台开发和国际化应用中。它提供了高效的 UTF-8 字符迭代器、编码转换函数和验证工具，完全符合 C++ 标准库风格。

## OHOS 适配要点

1. **Header-only 库特性**: utf8cpp 是纯头文件库，无需编译二进制文件，直接安装头文件即可使用
2. **测试禁用**: 测试代码依赖额外的链接配置，本预编译包禁用了测试套件
3. **镜像下载**: 中国大陆环境下建议使用 ghfast.top 等镜像加速 GitHub 源码下载

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| CMake | 3.28+ | 构建系统 |
| clang/clang++ | 系统默认 | 编译器 |

无外部库依赖。

## 功能验证

```bash
# 验证头文件安装
ls ~/usr/local/include/utf8cpp/
# 输出: utf8.h 等头文件

# C++ 程序中使用示例
# #include <utf8cpp/utf8.h>
# std::string str = "你好世界";
# utf8::iterator it(str.begin());
```

## 参考

- [官方仓库](https://github.com/nemtrif/utfcpp)
- [文档](https://github.com/nemtrif/utfcpp#documentation)