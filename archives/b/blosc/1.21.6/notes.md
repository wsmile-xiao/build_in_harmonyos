# blosc 1.21.6 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-04-24
- 编译器: clang
- 状态: success

## 编译步骤
```bash
cmake -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPREFER_EXTERNAL_ZSTD=ON \
  -DDEACTIVATE_SNAPPY=ON \
  -DBUILD_TESTS=OFF \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build build -j$(nproc)
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| - | 无重大问题 | - | - |

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| blosc-1.21.6-ohos-aarch64.tar.gz | 623KB | 预编译包 |
