# slang 2026.14 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-07-27
- 编译器: clang/clang++ 15.0.4
- 状态: built (待 conan-verify 后标 published)

## 编译步骤

1. init-build 下载源码 (tarball 不含 git 子模块)
2. 从 gitcode.com 镜像克隆 slang git 仓库获取子模块 SHA
3. 下载并放置必要的 git 子模块 (unordered_dense, miniz, lz4, cmark, vulkan, spirv-headers, spirv-tools, glslang, fast_float, lua) 到 external/ 目录
4. CMake 配置:
```bash
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DSLANG_LIB_TYPE=STATIC -DBUILD_SHARED_LIBS=OFF \
  -DSLANG_ENABLE_CUDA=OFF -DSLANG_ENABLE_OPTIX=OFF \
  -DSLANG_ENABLE_DXIL=OFF -DSLANG_ENABLE_TESTS=OFF \
  -DSLANG_ENABLE_EXAMPLES=OFF -DSLANG_ENABLE_SLANG_RHI=OFF \
  -DSLANG_ENABLE_GFX=OFF -DSLANG_SLANG_LLVM_FLAVOR=DISABLE \
  -DSLANG_EXCLUDE_DAWN=ON -DSLANG_EXCLUDE_TINT=ON \
  -DSLANG_ENABLE_SLANGD=OFF -DSLANG_ENABLE_REPLAYER=OFF \
  -DSLANG_ENABLE_PCH=OFF -DSLANG_STANDARD_MODULE_DEVELOP_BUILD=OFF
```
5. make -j2 (需要中途签名新编译的二进制文件)
6. make install DESTDIR=$TEST_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | 鸿蒙 Python 无 CA 证书 | 安装 Mozilla CA 证书 + 创建符号链接 |
| 2 | tarball 缺少 git 子模块 | GitHub release tarball 不含 submodule 内容 | 从 gitcode.com 镜像获取子模块 SHA，用 Python urllib 下载 |
| 3 | 缺失 `typename` 关键字 | clang 15 不支持 C++20 P0634R3 (省略 typename) | 添加 `typename` 关键字到 3 处 |
| 4 | `std::views::reverse` 不可用 | clang 15 libc++ 缺少 C++20 ranges 完整支持 | 替换为索引反向循环 |
| 5 | `std::views::values` 不可用 | 同上 | 替换为手动值提取 |
| 6 | `sleepCurrentThread` 链接错误 | CMake `UNIX` 变量在 HarmonyOS 未设置，导致 unix/ 目录被排除 | 修改 Glob.cmake 添加 HarmonyOS 平台匹配 |
| 7 | `Operation not permitted` 执行二进制 | 鸿蒙 ELF 签名要求 | 用 binary-sign-tool 签名所有新编译的二进制 |

## 源码修改

1. **source/core/slang-internally-linked-list.h** (line 122): 添加 `typename` 关键字
   - `using InternallyLinkedListNode = typename InternallyLinkedList<T>::Node;`
2. **source/slang/slang-fossil.h** (lines 110, 1132): 添加 `typename` 关键字
   - `using Fossilized = typename FossilizedTypeTraits<T>::FossilizedType;`
   - `using RelativePtrOffset = typename FossilizedPtr<void>::Offset;`
3. **source/compiler-core/slang-rich-diagnostics-render.cpp** (lines 613, 626): 替换 `std::views::reverse`
   - 使用索引反向循环替代 C++20 ranges
4. **source/slang/slang-capability.cpp** (lines 917, 926): 替换 `std::views::values`
   - 使用手动值提取替代 C++20 ranges
5. **cmake/Glob.cmake** (lines 36, 44): 添加 HarmonyOS 平台匹配
   - `if(NOT UNIX AND NOT CMAKE_SYSTEM_NAME MATCHES "OHOS|HarmonyOS")`
   - `if(NOT CMAKE_SYSTEM_NAME MATCHES "Windows|Linux|Darwin|OHOS|HarmonyOS")`

## 依赖版本

- 无外部 Conan 依赖 (所有依赖均为源码内嵌子模块)
- 子模块版本: 使用 slang v2026.14 标签指定的子模块 SHA

## 验证结果

```bash
# slangc 编译成功
$TEST_PREFIX/$DEFAULT_PREFIX/bin/slangc --version
# 生成静态库 libslang-compiler.a (314MB)
# 生成可执行文件: slangc (31MB), slangi (32MB), slang (195KB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/slangc | 31MB | Slang 独立编译器 |
| bin/slangi | 32MB | Slang 解释器 |
| bin/slang | 195KB | Slang 调度器 |
| lib/libslang-compiler.a | 314MB | Slang 编译器静态库 |
| lib/libslang-rt.a | 8.5MB | Slang 运行时库 |
| lib/libslang-glslang-2026.14.so | - | GLSLang 模块 |
| lib/libslang-glsl-module-2026.14.so | - | GLSL 模块 |
| include/slang.h | - | Slang 头文件 |

## 注意事项

1. 子模块不是从 tarball 获取的，需要单独下载
2. 编译过程中需要多次签名新编译的二进制文件 (E077)
3. slangc 是命令行工具，需要创建 commands.json (R38)
4. 构建为静态库 (SLANG_LIB_TYPE=STATIC, R26)
---

**编译结束**: 2026-07-27 13:19
**最终状态**: built
