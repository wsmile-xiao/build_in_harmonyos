# Basis Universal v2_1_0r 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-30
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 GitHub 下载 basis_universal v2_1_0r 源码
2. 使用 CMake 构建：
   ```bash
   cmake -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_SYSTEM_NAME=Linux \
         -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
   make -j2
   make install DESTDIR=$HOME/tmp/test-install-basisu-v2_1_0r
   ```
3. 预编译包制作：ohc package basisu v2_1_0r

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| basisu-v2_1_0r-ohos-aarch64.tar.gz | 9.8MB | 预编译包（编码器+库+头文件） |
| basisu-v2_1_0r-ohos-aarch64-debug.tar.gz | 420KB | 调试符号包 |