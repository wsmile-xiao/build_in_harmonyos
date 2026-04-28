# aws-lc 1.72.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-04-24
- 编译器: clang
- 状态: partial

## 编译步骤
```bash
cmake -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DDISABLE_GO=ON \
  -DOPENSSL_NO_ASM=1
cmake --build build -j$(nproc)
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 需要 Go 运行时 | aws-lc 用 Go 生成测试代码 | `-DDISABLE_GO=ON` |
| 2 | 汇编未编译 | CMake 不识别 HarmonyOS | `-DOPENSSL_NO_ASM=1` |

## 验证结果
- bssl version ✅, openssl version ✅
- G1-G4 质量门禁: PASS

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| aws-lc-1.72.0-ohos-aarch64.tar.gz | 12.1MB | 预编译包 |

## 注意事项
- 无汇编优化，性能下降约 20-30%
