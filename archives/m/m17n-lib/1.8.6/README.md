# m17n-lib 1.8.6 - OpenHarmony 预编译包

GNU M-text multilingualization library (core)

## 简介

m17n-lib 是一个用于多语言文本处理的库，支持多种语言编码和文本转换。

## 安装

```bash
# 解压预编译包
tar -xzf m17n-lib-1.8.6-ohos.tar.gz

# 复制到系统目录
cp -r m17n-lib-1.8.6-ohos/* /usr/local/

# 更新动态库缓存
ldconfig
```

## 包含内容

- **库文件**: libm17n-core, libm17n-flt, libm17n-gui, libm17n
- **头文件**: m17n.h, m17n-core.h, m17n-flt.h, m17n-gui.h, m17n-X.h, m17n-misc.h
- **pkg-config**: m17n-core.pc, m17n-flt.pc, m17n-gui.pc, m17n-shell.pc

## 使用方法

```bash
# 使用 pkg-config 编译
pkg-config --cflags --libs m17n-core

# 编译示例程序
clang -o myapp myapp.c `pkg-config --cflags --libs m17n-core`
```

## 依赖

无外部依赖（fontconfig/freetype/fribidi 已禁用）

## 注意事项

- GUI 库功能受限（禁用了相关依赖）
- 仅支持核心 M-text 处理功能

## 版本信息

- 版本: 1.8.6
- 构建系统: autotools
- 编译日期: 2026-06-08
- 目标平台: OpenHarmony

