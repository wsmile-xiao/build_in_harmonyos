# kuzu 0.11.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-03
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: published

## 编译步骤

1. 手动建立构建上下文（ohc-run.py init-build超时）
2. cmake 配置: `-DCMAKE_INSTALL_PREFIX=~/usr/local -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF -DBUILD_SHELL=OFF -DBUILD_PYTHON=OFF -DBUILD_JAVA=OFF -DBUILD_BENCHMARK=OFF -DBUILD_WASM=OFF`
3. cmake --build . -j2 (编译成功, ~600秒)
4. DESTDIR=$TEST_PREFIX cmake --install . (安装验证)
5. cmake --install . (安装到DEFAULT_PREFIX)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | simsimd动态分派(SVE/SVE2)编译失败 | OHOS aarch64不支持ARM SVE/SVE2 intrinsics(缺arm_sve.h) | 重写third_party/simsimd/lib.c为NEON-only stub，禁用动态分派 |
| 2 | std::ranges::any_of/sort/reverse/count_if不可用 | OHOS libc++不完全支持C++20 ranges库 | 替换为std::any_of/sort/reverse/count_if + begin/end迭代器 |
| 3 | std::erase_if/std::erase不可用 | OHOS libc++不提供C++20容器成员函数 | 使用erase-remove idiom替代 |
| 4 | InMemHashIndex<T>::OwnedType等缺少typename | Clang 15严格C++模式要求typename前缀 | 添加typename关键字到依赖类型名 |
| 5 | -latomic链接失败 | OHOS SDK不包含libatomic | 注释掉atomic库链接(aarch64硬件原生支持原子操作) |
| 6 | CMake提示"System is unknown to cmake" | HarmonyOS未注册到CMake平台数据库 | 非致命，不影响构建 |
| 7 | ohc-run.py init-build超时 | 大型tarball解压耗时 | 手动建立.build-context文件 |

## 源码修改（13个补丁）

| 补丁编号 | 修改文件 | 说明 |
|----------|----------|------|
| 0001 | CMakeLists.txt | 顶层添加HarmonyOS适配compile_definitions(禁用SVE/SVE2) |
| 0002 | extension/vector/src/index/hnsw_index.cpp | std::ranges::sort/reverse → std::sort/reverse |
| 0003 | src/CMakeLists.txt | 注释掉-latomic链接 |
| 0004 | src/storage/compression/compression.cpp | std::ranges::count_if(iota_view) → std::count_if + temp vector |
| 0005 | src/storage/compression/float_compression.cpp | std::ranges::count_if(iota_view) → std::count_if + temp vector |
| 0006 | src/storage/index/in_mem_hash_index.cpp | 添加typename关键字 |
| 0007 | src/storage/local_storage/local_rel_table.cpp | std::erase → erase-remove idiom |
| 0008 | src/storage/table/csr_node_group.cpp | std::erase_if → erase-remove idiom |
| 0009 | src/storage/table/rel_table.cpp | std::ranges::count → std::count |
| 0010 | src/transaction/transaction_manager.cpp | std::ranges::any_of → std::any_of + std::erase_if → erase-remove |
| 0011 | src/include/storage/index/hash_index.h | 添加typename |
| 0012 | src/include/storage/local_storage/local_hash_index.h | 添加typename |
| 0013 | third_party/simsimd/lib.c | 重写为NEON-only stub(禁用SVE/SVE2动态分派) |

## 产出文件
- libkuzu.so (21.1MB, ELF aarch64 shared library, 1985个导出函数符号, 167个kuzu_* API符号)
- libkuzu.a (57.2MB, 718个对象文件)
- kuzu.h (71KB, 1586行, C API头文件)

## cmake配置选项
```
-DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local
-DCMAKE_BUILD_TYPE=Release
-DBUILD_TESTS=OFF
-DBUILD_SHELL=OFF
-DBUILD_PYTHON=OFF
-DBUILD_JAVA=OFF
-DBUILD_BENCHMARK=OFF
-DBUILD_EXTENSION_TESTS=OFF
-DBUILD_WASM=OFF
-DBUILD_SINGLE_FILE_HEADER=OFF
```

---

**编译结束**: 2026-06-04
**最终状态**: published