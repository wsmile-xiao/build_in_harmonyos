# xbyak

## 简介
Xbyak 是 herumi 维护的 C++ header-only JIT 汇编器，支持 x86(IA-32)/x64(AMD64) 指令集，包括 MMX/SSE/SSE2/SSE3/SSSE3/SSE4/FPU/AVX/AVX2/AVX-512/APX/AVX10.2。

## OHOS 适配
- 纯头文件库（header-only），无需编译 .so
- 无外部依赖
- x86/x64 JIT 汇编器，在 aarch64 上仅验编译（cross_building 跳过运行时）
- test_package 验证 xbyak.h 可被 include + CodeGenerator 类可实例化 + getVersion() 版本号正确

## 依赖
- 无编译依赖
- 无运行时依赖

## 功能验证
```bash
# 编译测试程序（验证头文件可用）
clang++ test.cpp -o test_probe -I$CONAN_INCLUDE_DIRS_XBYAK
./test_probe
```

## 参考
- 主页: https://github.com/herumi/xbyak
- 安装文档: https://github.com/herumi/xbyak/blob/master/doc/install.md
