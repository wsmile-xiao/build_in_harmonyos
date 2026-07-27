# libstemmer 3.1.1 编译笔记

## 软件信息
- 上游: https://snowballstem.org/
- 许可证: BSD-3-Clause
- 构建系统: 简单 Makefile（无 configure 脚本）

## 编译步骤
1. `make -j1` — 编译所有 stemmer 源文件，生成 libstemmer.a 和 stemwords
2. 手动安装: `cp libstemmer.a $PREFIX/lib/`, `cp include/libstemmer.h $PREFIX/include/`

## 构建产物
- libstemmer.a — 静态库（包含 37 种语言的 stemmer）
- stemwords — 命令行示例工具
- include/libstemmer.h — 公共头文件

## 功能验证
- `echo "connected" | ./stemwords -l english` → "connect" ✓
- `echo "running" | ./stemwords -l english` → "run" ✓
- test_package 消费者测试: 3 个断言全部通过

## OHOS 适配说明
- 无需补丁，原始 Makefile 直接编译通过
- 编译器通过 Conan toolchain 传递 (CC, AR)
- 库名称: libstemmer.a → cpp_info.libs = ["stemmer"]（链接器 -lstemmer）
---

**编译结束**: 2026-07-16 00:50
**最终状态**: built
