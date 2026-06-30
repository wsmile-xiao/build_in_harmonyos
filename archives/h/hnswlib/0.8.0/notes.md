# hnswlib 0.8.0 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-06-25
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

1. 从 GitHub 下载源码 tarball (v0.8.0 tag)
2. 解压到工作目录
3. CMake 配置: `cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_CXX_COMPILER=clang++ .`
4. 编译: `make -j1`
5. DESTDIR 安装: `make install DESTDIR=$TEST_PREFIX`
6. 运行测试套件
7. 预编译包制作: `ohc-run.py package hnswlib 0.8.0`
8. 本地安装: `make install` (不带 DESTDIR)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络限制 | 使用 curl 下载到 $HOME/tmp 后用 file:// URL |
| 2 | init-build 卡在 SSL 证书更新 | 网络限制导致证书下载超时 | 手动创建 .build-context 文件 |
| 3 | clean_verify.py 不支持 CMake | 脚本硬编码 ./configure | 手动执行 G0 验证（从 tarball 重建成功） |
| 4 | G4 门禁失败 | manifest.yaml 缺少 build_system 顶层字段 | 添加 build_system: cmake 字段 |

## 源码修改

无补丁。hnswlib 0.8.0 源码无需任何修改即可在 OpenHarmony 上编译。

## 依赖版本

无外部依赖。hnswlib 是 header-only C++ 库，仅依赖 C++11 标准库。

## 验证结果

### 单元测试
- searchKnnCloserFirst_test: PASS
- searchKnnWithFilter_test: PASS
- multivector_search_test: PASS (recall: 0.979335/1.0)
- epsilon_search_test: PASS
- test_updates: SKIPPED (需要外部 config.txt)
- multiThreadLoad_test: SKIPPED (无限循环压测)
- multiThread_replace_test: SKIPPED (无限循环压测)
- main (sift_1b): SKIPPED (需要 SIFT 数据集)

### 功能验证
- 测试程序包含 hnswlib.h 并使用 L2Space 类编译运行成功

### 质量门禁
- G0 干净构建: PASS (手动验证)
- G1 二进制完整性: PASS (header-only 库，无二进制)
- G2 功能可用性: PASS (1 warning - header-only 无可执行测试)
- G3 可移植性: PASS
- G4 档案完整性: PASS

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| hnswlib-0.8.0-ohos-aarch64.tar.gz | 111KB | 预编译包（7个头文件 + 1个CMake配置） |

## 功能测试（2026-06-25）

### 测试程序
- 文件: `hnswlib_func_test.cpp`
- 编译: `clang++ -std=c++11 -O2 -I ~/usr/local/include -o hnswlib_func_test hnswlib_func_test.cpp -lpthread`
- 覆盖 10 个测试项，23 个断言点

### 测试结果

| # | 测试项 | 结果 |
|---|--------|------|
| T1 | L2 空间构建/插入/kNN/召回率 | ✅ PASS (召回率 1.0) |
| T2 | InnerProduct 空间 kNN | ✅ PASS |
| T3 | 序列化 saveIndex/loadIndex | ✅ PASS (结果完全一致) |
| T4 | 删除/恢复 markDelete/unmarkDelete | ✅ PASS |
| T5 | 索引扩容 resizeIndex | ✅ PASS |
| T6 | 过滤搜索 BaseFilterFunctor | ✅ PASS |
| T7 | searchKnnCloserFirst 排序 | ✅ PASS |
| T8 | 多线程并发 (4线程, 18486次搜索) | ✅ PASS |
| T9 | BruteforceSpace 暴力搜索对比 | ✅ PASS |
| T10 | 平台兼容性 (ARM标量路径) | ✅ PASS |

**总结: 23/23 PASS, 0 FAIL — hnswlib 0.8.0 在鸿蒙平台功能完全正常**

### 关键发现
1. L2 空间召回率 1.0（1000 向量, k=10, ef=50），精度无损
2. 多线程并发安全（4 线程搜索 + 2 线程插入，无崩溃）
3. ARM aarch64 无 SSE/AVX，自动降级标量实现，功能无影响
4. saveIndex/loadIndex 序列化可靠，可用于持久化
5. 全核心 API 覆盖：L2Space, InnerProductSpace, BruteforceSearch, addPoint, searchKnn, searchKnnCloserFirst, saveIndex, loadIndex, markDelete, unmarkDelete, resizeIndex, setEf, BaseFilterFunctor

## 注意事项

1. hnswlib 是 header-only 库，安装产物仅包含头文件和 CMake 配置文件，无 .so/.a 库文件
2. CMakeLists.txt 中使用了 -march=native 和 -Ofast 标志用于示例和测试编译，不影响库本身
3. clean_verify.py 脚本不支持 CMake 项目，G0 需手动验证
4. 部分测试需要外部数据文件（SIFT 数据集、config.txt），这些文件不包含在 release tarball 中
5. ARM aarch64 平台无 SSE/AVX 指令集，距离计算使用标量实现（L2Sqr / InnerProduct），性能低于 x86 SIMD 但功能完全正常
---

**编译结束**: 2026-06-25 11:20
**最终状态**: built
**功能测试**: 2026-06-25 11:48 — 23/23 PASS ✅
