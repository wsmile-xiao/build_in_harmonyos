# blake3

## 简介
BLAKE3 是一种快速的加密哈希函数，比 BLAKE2、SHA-1、SHA-2 和 SHA-3 更快。本软件为 C 实现，提供静态库和头文件。

## OHOS 适配
- 源码结构特殊：CMakeLists.txt 位于 c/ 子目录，init-build 会自动提升
- 使用 CMake 构建（非 autotools）
- aarch64 平台自动启用 NEON SIMD 优化
- 仅提供静态库 libblake3.a，无动态库

## 依赖
无外部依赖。

## 功能验证
```bash
cc -O3 -o example example.c -I$HOME/usr/local/include -L$HOME/usr/local/lib -lblake3
echo "Hello, BLAKE3!" | ./example
```

## 参考
- 官网: https://github.com/BLAKE3-team/BLAKE3
