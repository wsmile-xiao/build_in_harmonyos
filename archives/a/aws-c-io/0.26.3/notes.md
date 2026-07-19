# aws-c-io 0.26.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-04-24
- 编译器: clang
- 状态: partial

## 编译步骤
```bash
cmake -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DBYO_CRYPTO=ON
cmake --build build -j$(nproc)
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | s2n 依赖缺失 | 默认需要 s2n-tls | `-DBYO_CRYPTO=ON` 禁用 |

## 依赖版本
- aws-c-common 0.12.6
- aws-c-cal 0.9.13
- aws-c-compression 0.3.2

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| aws-c-io-0.26.3-ohos-aarch64.tar.gz | 703KB | 预编译包 |

## 注意事项
- BYO_CRYPTO=ON 禁用 TLS，不影响基本 IO
- 编译产物: libaws-c-io.a (422KB)
