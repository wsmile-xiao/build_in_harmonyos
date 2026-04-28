# Zstandard (zstd)

## 简介
Facebook 开发的快速实时压缩算法，提供高压缩比和高速解压，广泛用于数据存储和传输。

## OHOS 适配
- Makefile 构建，平台兼容性好
- 无需源码修改

## 依赖
- 标准 C 库

## 功能验证
```bash
zstd --version
echo "test" | zstd | zstd -d
```

## 参考
- 官网: https://facebook.github.io/zstd/
