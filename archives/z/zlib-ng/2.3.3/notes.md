# zlib-ng 2.3.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-04-24
- 编译器: clang
- 状态: published

## 编译步骤
```bash
cmake -B build -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
cmake --build build -j$(nproc)
cmake --install build
```
