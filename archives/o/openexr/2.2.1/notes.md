# openexr 2.2.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-19
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 安装依赖 IlmBase 2.2.1
   - 从 http://download.savannah.nongnu.org/releases/openexr/ilmbase-2.2.1.tar.gz 下载
   - 编译并安装到 ~/usr/local

2. Configure
   - 使用 CC=clang CXX=clang++ 指定编译器
   - 参数: --prefix=/storage/Users/currentUser/usr/local --disable-ilmbasetest

3. Make
   - make -j1 编译
   - 遇到 b44ExpLogTable 和 dwaLookups 运行时找不到 IlmBase 动态库问题
   - 解决方案: 使用静态库重新链接这两个程序

4. Make install
   - 成功安装到 ~/usr/local

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 找不到 C++ 编译器 | 系统无 g++，有 clang++ | 设置 CC=clang CXX=clang++ |
| 2 | 缺少 IlmBase 依赖 | openexr 需要 IlmBase 库 | 先编译安装 IlmBase 2.2.1 |
| 3 | b44ExpLogTable/dwaLookups 运行时找不到 IlmBase 动态库 | 鸿蒙动态链接器问题 | 使用静态库重新链接 |
| 4 | exrheader 运行时找不到动态库 | 鸿蒙动态链接器需要 ELF 签名 | 需后续处理（使用 ohc-run.py sign-elf） |

## 依赖版本

- IlmBase 2.2.1
- zlib（未使用，openexr 2.2.1 不需要 zlib）

## 验证结果

```bash
pkg-config --modversion OpenEXR
2.2.1  ✅

exrheader 运行 ❌（动态链接问题）
```

## 注意事项

- IlmBase 必须先编译并安装
- 动态链接问题需要使用 ELF 签名工具处理
---

**编译结束**: 2026-05-19 17:51
**最终状态**: built
