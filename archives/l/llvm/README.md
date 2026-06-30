# LLVM

LLVM (Low Level Virtual Machine) 是一个模块化的编译器基础设施项目，提供编译器前端、优化器、后端及运行时库。

## 软件简介

LLVM 项目包含多个核心组件：

- **LLVM Core**: 提供独立于源码和目标的优化器，以及代码生成器
- **Clang**: C/C++/Objective-C 编译器前端
- **LLDB**: 调试器
- **compiler-rt**: 运行时库（builtins, sanitizer 运行时等）
- **libc++**: C++ 标准库实现

## OHOS 适配要点

### 平台识别

LLVM 源码中需要修改以下文件以支持 HarmonyOS 平台识别：

1. **config.guess**: 添加 HarmonyOS case 分支
   ```
   *:HarmonyOS:*:*)
       echo "${MACHINE}-unknown-linux-ohos"
       exit ;;
   ```

2. **HandleLLVMOptions.cmake**: 将 HarmonyOS 加入 UNIX 分支
   ```cmake
   elseif(FUCHSIA OR UNIX OR CMAKE_SYSTEM_NAME MATCHES "HarmonyOS")
   ```

### 编译配置

推荐使用系统 clang (15.0.4) 作为编译器，而非自编译 clang 18：

```bash
cmake -G "Unix Makefiles" \
  -DCMAKE_C_COMPILER=/path/to/ohos-sdk/llvm/bin/clang \
  -DCMAKE_CXX_COMPILER=/path/to/ohos-sdk/llvm/bin/clang++ \
  -DLLVM_TARGETS_TO_BUILD="AArch64" \
  -DCMAKE_BUILD_TYPE=Release \
  ../llvm
```

### 已知问题

1. **clang 18 编译卡住**: 在工具链阶段可能出现编译停滞，建议使用系统 clang
2. **Python libintl**: Python 运行时库依赖问题可能导致生成脚本失败
3. **ELF 签名**: 自编译工具需要 ELF 签名才能在 HarmonyOS 上执行

## 依赖关系

### 编译依赖

| 依赖 | 版本要求 | 说明 |
|------|---------|------|
| cmake | >= 3.20 | 构建系统 |
| python | >= 3.8 | 构建脚本 |
| ninja/make | - | 构建工具 |

### 运行时依赖

无运行时依赖（静态库）

## 产物说明

### 静态库 (114个)

位置: `~/usr/local/lib/llvm-18.1.8/`

核心库：
- `libLLVMCore.a` - LLVM 核心库
- `libLLVMCodeGen.a` - 代码生成库
- `libLLVMAnalysis.a` - 分析库
- `libLLVMAArch64Desc.a` - AArch64 目标描述
- `libLLVMSupport.a` - 支持库

### 运行时库

位置: `~/usr/local/lib/clang/18/lib/aarch64-linux-ohos/`

- `libclang_rt.builtins-aarch64.a` - clang 内置函数运行时库

### 工具

位置: `~/usr/local/bin/llvm-18-tools/`

- `clang-format` - 代码格式化工具
- `diagtool` - 诊断工具
- `llvm-tblgen` - TableGen 工具
- `clang-tblgen` - Clang TableGen 工具

## 版本状态

| 版本 | 状态 | 完成度 | 说明 |
|------|------|--------|------|
| 18.1.8 | partial | 90% | 静态库和运行时库已生成，建议使用系统 clang 15.0.4 替代 |

## 参考资料

- [LLVM 官方文档](https://llvm.org/docs/)
- [LLVM 编译指南](https://llvm.org/docs/GettingStarted.html)
- [HarmonyOS 编译器开发指南](https://gitee.com/openharmony/docs)