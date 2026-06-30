# scudo-malloc 19.1.6 适配笔记

## 编译环境
- 构建系统: cmake (LLVM compiler-rt 子项目)
- 编译日期: 2026-06-08
- 编译器: clang/clang++
- 状态: built (部分限制)

## 编译步骤

1. 提取 LLVM 19.1.6 源码包
2. 进入 compiler-rt 子目录
3. 配置 CMake，关键参数：
   - `-DCMAKE_SYSTEM_NAME=Linux`（欺骗 CMake，绕过 OS_NAME 检查）
   - `-DCOMPILER_RT_SANITIZERS_TO_BUILD=scudo_standalone`
   - 禁用其他组件（xray、libfuzzer、profile 等）
4. 构建：`make scudo_standalone`
5. 安装：`make install-scudo_standalone`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 无法识别 OHOS 平台 | LLVM compiler-rt 只支持 Linux/Darwin/Windows | `-DCMAKE_SYSTEM_NAME=Linux` 欺骗 CMake |
| 2 | 预扫描显示 pthread_cancel/mremap 不可用 | musl/OHOS 不支持这些 syscall | 已记录，可能影响功能 |
| 3 | 编译依赖 LLVM 构建系统 | compiler-rt 需要完整的 LLVM cmake 模块 | 使用完整 LLVM 源码树编译 |

## 源码修改

无补丁文件，仅配置修改。

## 依赖版本

- LLVM 19.1.6 (compiler-rt 子项目)
- clang 15.0.4

## 验证结果

编译产物：
- libclang_rt.scudo_standalone-aarch64.a (788KB)
- libclang_rt.scudo_standalone_cxx-aarch64.a (397KB)
- libclang_rt.scudo_standalone-aarch64.so (674KB，未签名)

**⚠️ 注意**：动态库无法签名，可能在 OHOS 上无法执行。建议使用静态库。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| scudo-malloc-19.1.6-ohos-aarch64.tar.gz | 1.1MB | 预编译包（静态库） |

## 注意事项

1. **平台限制**：scudo-malloc 依赖 pthread_cancel、mremap 等 syscall，OHOS 上不可用
2. **建议使用静态库**：动态库未签名，可能无法执行
3. **需要进一步测试**：在实际 OHOS 环境中验证功能可用性