# Zopfli

## 简介
Google 开发的压缩库，能生成比标准 zlib 更小的 gzip/zlib 输出（压缩比提升 3-8%），但速度较慢。

## OHOS 适配
- Makefile 构建，无 configure 步骤
- 需添加 install 目标支持 DESTDIR 安装

## 依赖
- 标准 C 库

## 功能验证
```bash
zopfli --help
zopflipng --help
```

## 参考
- 源码: https://github.com/google/zopfli
