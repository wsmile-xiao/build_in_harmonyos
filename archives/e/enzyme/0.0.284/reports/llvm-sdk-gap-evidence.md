# OHOS SDK LLVM 15 工具链缺口证据 — enzyme 0.0.284

> **报告目的**: 证明 OHOS SDK LLVM 15 缺失完整 LLVM 插件/lit/TableGen 组件，导致 enzyme 等 LLVM pass/plugin 类库无法完整构建与运行上游测试。支撑路径 B 候选与路径 C 候选（需官方确认）。
> **生成日期**: 2026-07-23
> **知识库**: E216-draft-enzyme-llvm-sdk-lit-ohos

## OHOS SDK LLVM 安装位置

```
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/
├── bin/   (clang, lld, llvm-strip 等)
├── lib/   (libLLVM-15.so 单体共享库)
└── lib/cmake/llvm/  (LLVMConfig.cmake, LLVMExports.cmake, AddLLVM.cmake 等)
```

## 缺口清单

### 缺口 1: LLVMExports.cmake 引用不存在的 .a stub

**验证命令**:
```bash
ls /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/*.a
# → No such file or directory (exit 1)
ls /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/cmake/llvm/LLVMExports.cmake
# → 存在，但内容引用 LLVMDemangle.a 等不存在的 .a
```

**复现错误**:
```
CMake Error at .../llvm/lib/cmake/llvm/LLVMExports.cmake:1150 (message):
  Library 'LLVMDemangle' not found
```

**规避方案**: cmake-overlay/LLVMConfig.cmake 跳过 LLVMExports.cmake，创建指向 libLLVM-15.so 的 IMPORTED target。

### 缺口 2: llvm-tblgen 二进制缺失

**验证命令**:
```bash
ls /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/llvm-tblgen
# → No such file or directory (exit 1)
```

**复现错误**:
```
Enzyme/CallDerivatives.cpp:2254:9: error: use of undeclared identifier 'handleBLAS'
Enzyme/Utils.cpp:410:14: error: use of undeclared identifier 'attributeTablegen'
```

**规避方案**: cmake-overlay/stub-tblgen.sh（需 chmod +x）生成最小 .inc 桩文件，提供 return false 的 handleBLAS/attributeTablegen。

### 缺口 3: lit / llvm-lit 缺失

**验证命令**:
```bash
which lit; echo "lit exit=$?"
# → exit 1（未安装）
which llvm-lit; echo "llvm-lit exit=$?"
# → exit 1（未安装）
ls /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/lit
# → No such file or directory
```

**复现错误**:
```
$ ninja check-enzyme
/bin/sh: lit: command not found
```

**规避方案**: build() 中跳过 enzyme/test 子目录；上游测试写 0/1523（未执行）。

### 缺口 4: 单体 libLLVM-15.so 符号导出缺口

**验证命令**:
```bash
nm -D /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/libLLVM-15.so | grep -c "llvm::cl::Option::setArgStr"
# → 0（未导出）
```

**复现错误**（test_enzyme runtime 加载）:
```
Error relocating libLLVMEnzyme-15.so: _ZN4llvm2cl6Option9setArgStrENS_9StringRefE: symbol not found
Error relocating libLLVMEnzyme-15.so: _ZN4llvm8demangle...: symbol not found
... (数百个 LLVM C++ API 符号 not found)
```

**规避方案**: test_package 先 dlopen("libLLVM-15.so", RTLD_NOW|RTLD_GLOBAL) 预加载 LLVM 符号；若 dlopen(libLLVMEnzyme-15.so) 仍因符号缺口失败，return 1（R34，无 false pass）。此为 OHOS SDK LLVM 工具链缺口，**路径 C 候选，需官方确认**。

### 缺口 5: AddLLVM.cmake 不完整

**验证命令**:
```bash
grep -c "function(tablegen\|function(add_llvm_library\|function(add_public_tablegen_target" /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/cmake/llvm/AddLLVM.cmake
# → 0 或不完整（缺上述函数定义）
```

**规避方案**: cmake-overlay/AddLLVM.cmake stub 实现 tablegen()/add_llvm_library()/add_public_tablegen_target()/configure_lit_site_cfg()/get_llvm_lit_path()。

## 现有知识库覆盖情况

| 条目 | 覆盖范围 | 是否覆盖本组合问题 |
|------|---------|-------------------|
| E120 | lld 动态链接 libxml2.so.16 路径问题 | ❌ |
| E132 | lld 运行时依赖 libxml2，LD_LIBRARY_PATH | ❌ |
| **E216 draft** | LLVMExports .a stub / LLVMDemangle / TableGen/tblgen / lit/FileCheck/llvm-lit / 单体 .so 符号导出 / LLVM CMake 函数 | ✅（本 draft） |

## 路径 C 候选问题（需官方确认）

1. OHOS SDK LLVM 15 是否会补充 .a stub 文件以支持 LLVMExports.cmake？
2. OHOS SDK LLVM 15 是否会提供 llvm-tblgen 以支持 TableGen 代码生成？
3. OHOS SDK LLVM 15 是否会提供 lit/FileCheck/llvm-lit 以支持上游 LLVM lit 测试体系？
4. 单体 libLLVM-15.so 是否会导出完整 LLVM C++ API 符号以支持插件 runtime 加载？
5. 上述工具链缺口是否算"系统级高难"，路径 C 候选分值以官方审核为准？

---

*evidence: llvm-sdk-gap-evidence.md · 2026-07-23 · PR !2786 · E216 draft*