# MurmurHash3

MurmurHash3 is a non-cryptographic hash function created by Austin Appleby, part of the SMHasher repository.

## 基本信息

- **名称**: MurmurHash3
- **主页**: https://github.com/aappleby/smhasher
- **许可证**: Public Domain
- **分类**: library

## 鸿蒙适配要点

- 上游使用 hancho 自定义构建系统，conanfile.py 用自定义 CMakeLists.txt 替换
- 只构建 MurmurHash3.cpp（上游 CMakeLists.txt 构建全部哈希函数）
- 无外部依赖，纯 C++ 单文件库

## API

提供三个哈希函数：
- `MurmurHash3_x86_32` — 32-bit hash
- `MurmurHash3_x86_128` — 128-bit hash (x86)
- `MurmurHash3_x64_128` — 128-bit hash (x64)
