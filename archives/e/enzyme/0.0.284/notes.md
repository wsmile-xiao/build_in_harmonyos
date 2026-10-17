# enzyme 0.0.284 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-17
- 编译器: clang 15.0.4 / clang++ 15.0.4 (OHOS SDK aarch64)
- 目标平台: aarch64-unknown-linux-ohos
- 状态: built

## 编译步骤

```bash
# 1. 配置 CMake
cmake -G Ninja .. \
  -DLLVM_DIR=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/cmake/llvm \
  -DCMAKE_BUILD_TYPE=Release \
  -DENZYME_ENABLE_PLUGINS=ON \
  -DENZYME_CLANG=OFF \
  -DENZYME_MLIR=OFF \
  -DENZYME_FORTRAN=OFF \
  -DENZYME_STATIC_LIB=OFF \
  -DENZYME_EXTERNAL_SHARED_LIB=OFF

# 2. 编译
ninja -j2

# 3. 产物
# Enzyme/libLLVMEnzyme-15.so (5.1 MB)
# Enzyme/libLLDEnzyme-15.so (5.1 MB)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | LLVM cmake 配置引用不存在的 .a 静态库 | OHOS SDK 的 LLVM 仅提供共享库(.so) | 创建自定义 LLVM cmake overlay，重写 LLVMConfig.cmake 使用共享库模式 |
| 2 | enzyme-tblgen 无法链接 | OHOS SDK 的 LLVM 不包含 TableGen 组件 | 跳过 enzyme-tblgen 构建，提供预生成的 .inc 文件 |
| 3 | -Werror=unused-variable 编译错误 | 源文件中 auto mod 变量未被使用 | 添加 (void)mod 抑制警告（补丁 0001/0002） |
| 4 | 源 tarball 嵌套目录结构 | Enzyme 源码在 enzyme/ 子目录下 | conanfile.py 中 cmake.configure(build_script_folder=self.source_folder/enzyme) |

## 源码修改

- `0001-Enzyme-AdjointGenerator.h.patch`: 在 AdjointGenerator.h 中添加 (void)mod，抑制未使用变量编译错误
- `0002-Enzyme-CallDerivatives.cpp.patch`: 在 CallDerivatives.cpp 中添加 (void)mod，抑制未使用变量编译错误
- `0003-tools-CMakeLists.txt.patch`: 跳过 enzyme-tblgen 构建子目录（OHOS SDK 不包含 LLVM TableGen）

## 依赖版本

- LLVM 15.0.4 (系统工具链，非 conan 包)
- 路径: /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/

## 验证结果

```bash
# 验证编译产物
file Enzyme/libLLVMEnzyme-15.so
# ELF 64-bit LSB shared object, ARM aarch64, ...

# 验证符号存在
nm -D Enzyme/libLLVMEnzyme-15.so | grep __enzyme_autodiff
```

## 注意事项

- Enzyme 的完整功能需要 LLVM TableGen 组件，OHOS SDK 不包含此组件
- 上游的 lit 测试套件无法在 OHOS SDK 环境中运行
- conan create 从源码构建受 LLVM 依赖限制，无法在 CI 中完整重建
- 如需完整功能，需在 CI 环境中配置完整的 LLVM 15 SDK（含 TableGen 和静态库）
---

**编译结束**: 2026-07-17 12:03
**最终状态**: built