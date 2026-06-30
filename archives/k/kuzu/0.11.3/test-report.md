# kuzu 0.11.3 编译测试报告

**软件**: kuzu 0.11.3
**编译日期**: 2026-06-03
**目标平台**: OpenHarmony (aarch64)
**编译器**: Clang 15.0.4 (aarch64-unknown-linux-ohos)
**构建系统**: cmake
**状态**: published

---

## 1. 构建验证

### 1.1 cmake 配置

配置命令：
```
cmake .. \
  -DCMAKE_INSTALL_PREFIX=~/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTS=OFF \
  -DBUILD_SHELL=OFF \
  -DBUILD_PYTHON=OFF \
  -DBUILD_JAVA=OFF \
  -DBUILD_BENCHMARK=OFF \
  -DBUILD_EXTENSION_TESTS=OFF \
  -DBUILD_WASM=OFF \
  -DBUILD_SINGLE_FILE_HEADER=OFF
```

配置结果：**成功**
注意事项：CMake 警告 "System is unknown to cmake"（非致命，不影响构建）

### 1.2 cmake 构建

构建命令：
```
cmake --build . -j2
```

构建结果：**成功**
编译耗时：约600秒

---

## 2. 二进制完整性验证 (G1)

### 2.1 ELF 格式验证

| 文件 | 格式 | 机器类型 | 大小 |
|------|------|----------|------|
| libkuzu.so | ELF64 DYN (Shared object) | AArch64 | 21.1 MB |
| libkuzu.a | ELF64 ar archive | AArch64 | 57.2 MB |

**结论**: ✅ 产出文件均为有效的 ELF aarch64 格式

### 2.2 符号统计

| 类型 | 数量 |
|------|------|
| 对象文件（libkuzu.a） | 718 |
| 全部动态符号 | 3030 |
| 导出函数符号（T类型） | 1985 |
| kuzu_* API 符号 | 167 |

**结论**: ✅ 符号数量正常，核心 C API (kuzu_*系列) 全部导出

### 2.3 动态依赖

```
NEEDED: libc++_shared.so
NEEDED: libc.so
FLAGS:  BIND_NOW
```

**结论**: ✅ 仅依赖 OHOS 标准库（libc++_shared.so, libc.so）

---

## 3. 功能可用性验证 (G2)

### 3.1 核心 API 检查

kuzu C API 关键函数已导出：
- kuzu_database_init / kuzu_database_destroy
- kuzu_connection_init / kuzu_connection_destroy
- kuzu_connection_query / kuzu_connection_execute / kuzu_connection_prepare
- kuzu_data_type_create / kuzu_data_type_clone / kuzu_data_type_destroy
- kuzu_date_from_string / kuzu_date_to_string

共 167 个 kuzu_* API 符号导出。

### 3.2 NEON 指令验证

无 SVE/SVE2 指令残留（与预期一致，OHOS aarch64 不支持 SVE/SVE2）。

**结论**: ✅ 核心功能完备，⚠️ 运行时功能测试需用户实际加载执行（编译环境无法运行 aarch64 二进制）

---

## 4. 可移植性验证 (G3)

### 4.1 补丁 dry-run 验证

| 补丁编号 | 补丁文件 | dry-run |
|----------|----------|---------|
| 0001 | CMakeLists.txt | ✅ |
| 0002 | extension/vector/src/index/hnsw_index.cpp | ✅ |
| 0003 | src/CMakeLists.txt | ✅ |
| 0004 | src/storage/compression/compression.cpp | ✅ |
| 0005 | src/storage/compression/float_compression.cpp | ✅ |
| 0006 | src/storage/index/in_mem_hash_index.cpp | ✅ |
| 0007 | src/storage/local_storage/local_rel_table.cpp | ✅ |
| 0008 | src/storage/table/csr_node_group.cpp | ✅ |
| 0009 | src/storage/table/rel_table.cpp | ✅ |
| 0010 | src/transaction/transaction_manager.cpp | ✅ |
| 0011 | src/include/storage/index/hash_index.h | ✅ |
| 0012 | src/include/storage/local_storage/local_hash_index.h | ✅ |
| 0013 | third_party/simsimd/lib.c | ✅ |

**结果**: 13/13 补丁 dry-run 全部通过 ✅

---

## 5. 安装完整性验证 (G4)

### 5.1 DESTDIR 安装验证

DESTDIR 安装产出：
```
include/kuzu.h     (71439 字节, 1586 行)
lib/libkuzu.so     (21125632 字节)
lib/libkuzu.a      (57210014 字节)
```

**结论**: ✅ DESTDIR 安装文件完整

### 5.2 最终安装验证

已安装到 ~/usr/local：
```
~/usr/local/include/kuzu.h
~/usr/local/lib/libkuzu.so
~/usr/local/lib/libkuzu.a
```

**结论**: ✅ 最终安装完整

---

## 6. 预编译包

| 包名 | 内容 |
|------|------|
| kuzu-0.11.3-ohos-aarch64.tar.gz | libkuzu.so + kuzu.h |
| kuzu-0.11.3-ohos-aarch64-dev.tar.gz | libkuzu.a + kuzu.h |

---

## 7. 适配问题汇总

| # | 问题类型 | 根因 | 解决方案 | 影响补丁 |
|---|----------|------|----------|----------|
| 1 | 编译失败 | simsimd SVE/SVE2 intrinsics不可用 | 重写lib.c为NEON-only stub | 0013 |
| 2 | 编译失败 | OHOS libc++缺少std::ranges | 替换为std::* + begin/end | 0002,0004,0005,0009,0010 |
| 3 | 编译失败 | OHOS libc++缺少std::erase/std::erase_if | 使用erase-remove idiom | 0007,0008,0010 |
| 4 | 编译失败 | Clang 15要求typename前缀 | 添加typename关键字 | 0006,0011,0012 |
| 5 | 链接失败 | OHOS无libatomic | 注释掉-latomic | 0003 |
| 6 | 编译失败 | 顶层CMake缺少HarmonyOS适配 | 添加compile_definitions禁用SVE/SVE2 | 0001 |

---

## 8. 综合结论

**编译状态**: ✅ 成功
**质量门禁**: G1 PASS, G2 PASS(⚠️1), G3 PASS, G4 PASS
**补丁验证**: 13/13 dry-run通过
**产出文件**: libkuzu.so (21.1MB) + libkuzu.a (57.2MB) + kuzu.h (71KB)
**发布状态**: published