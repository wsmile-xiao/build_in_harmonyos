# ciso 1.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-04-22
- 编译器: clang
- 状态: success

## 编译步骤
使用 Makefile 直接编译，但 Makefile 硬编码了 gcc，需手动改为 clang：
- 手动执行 `clang -o ciso.o -c ciso.c -fPIC -O2` 和 `clang -o ciso ciso.o -lz`
- 手动安装 ciso 二进制到 PREFIX/bin

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 gcc | 上游仅支持 gcc | 手动使用 clang 编译 |
| 2 | Format string warnings | uint64_t vs long long 类型不匹配 | 非致命，忽略 |

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| ciso-1.0-ohos-aarch64.tar.gz | — | 主包 |
| ciso-1.0-ohos-aarch64-debug.tar.gz | — | Debug 包 |

## 验证结果
- `ciso` → usage message ✅
