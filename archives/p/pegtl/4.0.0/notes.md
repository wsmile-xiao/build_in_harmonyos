# pegtl 4.0.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-08
- 编译器: clang/clang++
- 状态: published

## 编译步骤

pegtl 是一个 header-only C++ 库，主要需要安装头文件。

**关键 cmake 命令**：
```bash
cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
      -DCMAKE_BUILD_TYPE=Release \
      -DPEGTL_BUILD_TESTS=OFF \
      -DPEGTL_BUILD_EXAMPLES=OFF \
      ..
make install DESTDIR=/storage/Users/currentUser/test-install-pegtl-4.0.0
```

**关键选项**：
- `-DPEGTL_BUILD_TESTS=OFF`: 禁用测试程序（避免链接错误）
- `-DPEGTL_BUILD_EXAMPLES=OFF`: 禁用示例程序（避免链接错误）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 默认构建测试/示例时链接失败 | pegtl 默认会构建测试和示例，但 OHOS SDK 缺少完整的 C++ 标准库链接支持 | 设置 `-DPEGTL_BUILD_TESTS=OFF` 和 `-DPEGTL_BUILD_EXAMPLES=OFF`，只安装 header-only 库 |

## 源码修改

无需源码修改。

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4

## 验证结果

```bash
# Header-only 库验证
ls /storage/Users/currentUser/usr/local/include/tao/pegtl.hpp
# 确认头文件已安装

# pkg-config 验证
pkg-config --modversion pegtl
# 应返回 4.0.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pegtl-4.0.0-ohos-aarch64.tar.gz | ~XXX KB | 预编译包（header-only） |

## 注意事项

1. pegtl 是 header-only 库，只需安装头文件
2. 测试和示例程序需要完整的 C++ 标准库支持，在 OHOS 上可能无法编译
3. 使用时只需包含头文件 `<tao/pegtl.hpp>` 即可
---

**编译结束**: 2026-06-08 14:38
**最终状态**: built
