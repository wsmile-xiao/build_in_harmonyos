# llvm 18.1.8 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-09
- 编译器: clang 15.0.4 (OpenHarmony SDK)
- 状态: partial (90% 完成)

## 源码信息
- 源码包: llvm-project-18.1.8.src.tar.xz (126MB)
- 包含子项目: llvm, clang, bolt, compiler-rt 等
- 解压位置: /storage/Users/currentUser/tmp/builds/llvm-project-18.1.8.src

## 编译步骤

### 1. 修补配置文件
```bash
# 修补 config.guess 支持 HarmonyOS
# 在 llvm/cmake/config.guess 中添加 HarmonyOS case 分支

# 修补 HandleLLVMOptions.cmake
# 在 elseif(FUCHSIA OR UNIX) 条件中添加 HarmonyOS 支持
```

### 2. cmake 配置
```bash
cmake -G "Unix Makefiles" \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_C_COMPILER=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang++ \
  -DCMAKE_AR=/data/service/hnp/bin/ar \
  -DCMAKE_RANLIB=/data/service/hnp/bin/ranlib \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLVM_TARGETS_TO_BUILD="AArch64" \
  -DLLVM_ENABLE_PROJECTS="" \
  ../llvm-project-18.1.8.src/llvm
```

### 3. 编译
```bash
cd /storage/Users/currentUser/tmp/builds/llvm-18.1.8.build
make -j2
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | clang 18 无法链接程序 | 缺少 crt*.o 运行时启动文件 | 使用系统 clang 15.0.4 |
| 2 | llvm-ar 执行报 "Operation not permitted" | 未签名 ELF 文件 | 使用系统 GNU ar |
| 3 | config.guess 无法识别 HarmonyOS | 旧版脚本不支持新系统 | 手动添加 HarmonyOS case 分支 |
| 4 | cmake 报 "Unable to determine platform" | HandleLLVMOptions.cmake 不识别 HarmonyOS | 添加 HarmonyOS 到 UNIX 分支 |
| 5 | Python libintl.so.8 加载失败 | Python 运行时库依赖问题 | 未完全解决，导致编译在90%时中断 |

## 源码修改

### llvm/cmake/config.guess
添加 HarmonyOS 系统识别分支：
```bash
*:HarmonyOS:*:*)
    case "$UNAME_MACHINE" in
        aarch64|arm64) MACHINE=aarch64 ;;
        armv7*|armv8*) MACHINE=arm ;;
        x86_64|amd64)  MACHINE=x86_64 ;;
        i?86)         MACHINE=i686 ;;
        *)            MACHINE="$UNAME_MACHINE" ;;
    esac
    echo "${MACHINE}-unknown-linux-ohos"
    exit ;;
```

### llvm/cmake/modules/HandleLLVMOptions.cmake
修改第181行：
```cmake
elseif(FUCHSIA OR UNIX OR CMAKE_SYSTEM_NAME MATCHES "HarmonyOS")
```

## 已生成的产物

### 静态库（114个，591MB）
位置: /storage/Users/currentUser/usr/local/lib/llvm-18.1.8/

核心库文件：
- libLLVMCore.a (7.8M) - LLVM 核心库
- libLLVMCodeGen.a (16M) - 代码生成库
- libLLVMAnalysis.a (9.2M) - 分析库
- libLLVMAArch64Desc.a (2.4M) - AArch64 目标描述
- libLLVMSupport.a - 支持库
- libLLVMDemangle.a - 符号解修饰库

### clang 运行时库
位置: /storage/Users/currentUser/usr/local/lib/clang/18/lib/aarch64-linux-ohos/
- libclang_rt.builtins-aarch64.a (361KB) - clang 内置函数运行时库

## 未完成的产物

由于 Python libintl 问题导致编译在90%时中断：
- clang 可执行文件及工具链
- 部分 clang 库（clangTooling 等）
- 头文件和 cmake 配置文件

## 验证结果

```bash
# 验证静态库数量
ls ~/usr/local/lib/llvm-18.1.8/*.a | wc -l
# 输出: 114

# 验证 clang 运行时库
ls ~/usr/local/lib/clang/18/lib/aarch64-linux-ohos/
# 输出: libclang_rt.builtins-aarch64.a
```

## 后续工作

**已采用替代方案**：使用系统 clang 15.0.4 替代 clang 18

原因：
- clang 18 编译在工具链阶段卡住
- 系统 clang 15.0.4 已完整可用，有 ELF 签名
- 已生成的静态库足以支持其他软件的链接需求
- clang 运行时库 `libclang_rt.builtins` 已生成

## 最终安装产物

| 产物 | 位置 | 用途 |
|------|------|------|
| LLVM 静态库 (114个) | ~/usr/local/lib/llvm-18.1.8/ | 静态链接支持 |
| clang 运行时库 | ~/usr/local/lib/clang/18/lib/aarch64-linux-ohos/ | clang 内置函数 |
| clang 工具 | ~/usr/local/bin/llvm-18-tools/ | clang-format, diagtool 等 |
| clang 头文件 | ~/usr/local/include/llvm-18/include/ | 编译头文件 |

## 注意事项

- LLVM 编译时间长（约3小时），建议使用 -j2 避免系统过载
- clang 运行时库（libclang_rt.builtins）对于使用 clang 编译其他软件至关重要
- 修补的 config.guess 和 HandleLLVMOptions.cmake 需要保存为补丁文件

---

**编译结束**: 2026-06-09 17:58
**最终状态**: partial (90%)
**替代方案**: 使用系统 clang 15.0.4 替代 clang 18
**审核结果**: 待补充软件级 manifest.yaml 和 README.md 后重新审核

## 功能测试报告

**测试日期**: 2026-06-09
**测试评分**: 7.6/10
**测试报告**: reports/test-report.md

### 测试结果摘要

| 测试项 | 状态 | 评分 |
|--------|------|------|
| LLVM 静态库（114个，220MB） | ✅ PASS | 10/10 |
| clang 运行时库（353KB） | ✅ PASS | 10/10 |
| clang 工具（4个，18MB） | ⚠️ PARTIAL | 5/10 |
| clang 头文件（245个） | ✅ PASS | 10/10 |
| LLVM 开发头文件 | ❌ MISSING | 3/10 |

### 功能可用性

- **静态链接**: ✅ 可用 - 114 个 LLVM 静态库可用于链接其他软件
- **运行时支持**: ✅ 可用 - libclang_rt.builtins 支持 clang 编译器运行时
- **编译头文件**: ✅ 可用 - 245 个 clang 头文件可用于编译程序
- **clang 工具**: ⚠️ 部分 - clang-format 等工具缺少 libzstd.so.1 依赖
- **LLVM 开发**: ⚠️ 部分 - 缺少 LLVM 开发头文件（llvm/Support/*.h）

### 建议

1. 使用系统 clang 15.0.4 作为主要编译器
2. LLVM 静态库可用于静态链接开发
3. clang 工具需安装 libzstd 库后使用

---

## 预编译包

**打包日期**: 2026-06-09
**文件名**: llvm-18.1.8-ohos-aarch64.tar.gz
**大小**: 263MB
**sha256**: 7f477cf3b675474809fb8fb81c45237a57d3f2cfef5b54893391e5460c0b03db

### 包含内容

| 内容 | 数量/大小 |
|------|----------|
| LLVM 静态库 | 114个 (220MB) |
| clang 运行时库 | 353KB |
| clang 工具 | 4个 (19MB) |
| clang 头文件 | 245个 (16MB) |

### 安装说明

```bash
# 解压到 /usr/local
tar -xzf llvm-18.1.8-ohos-aarch64.tar.gz -C /usr/local

# 产物位于 llvm-18.1.8/ 目录
ls llvm-18.1.8/
# lib/llvm-18.1.8/       - LLVM 静态库
# lib/clang/18/          - clang 运行时库
# bin/llvm-18-tools/     - clang 工具
# include/llvm-18/       - clang 头文件
```