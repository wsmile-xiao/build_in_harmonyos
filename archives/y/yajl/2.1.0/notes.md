# yajl 2.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-04-24
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤
```bash
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake GET_TARGET_PROPERTY LOCATION 废弃 | CMake 4.x 不支持旧语法 | 使用生成器表达式 $<TARGET_FILE:target> 替代 |
| 2 | libyajl.so 无 SONAME 字段（readelf -d 无 SONAME 输出） | CMake 4.1.2 无 Platform/HarmonyOS.cmake 模块，CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 未设置，链接命令中 soname 被省略 | conanfile generate() 中 tc.cache_variables 显式设置 CMAKE_SHARED_LIBRARY_SONAME_C_FLAG/CXX_FLAG=-Wl,-soname,（草稿知识 E322） |

## 源码修改
- 0001-reformatter-CMakeLists.txt.patch: 替换 LOCATION 属性
- 0002-verify-CMakeLists.txt.patch: 替换 LOCATION 属性

## 验证结果
- L0: pass（conan create 成功）
- L1: pass（test_package ctest 通过：yajl_tree_parse/yajl_tree_get）
- L2: skip（json_verify/json_reformat 为 aarch64 OHOS ELF 交叉编译产物，主机非目标平台不可直接运行；yajl CLI 不支持 --version/-h，逻辑由 L1 ctest 覆盖）
- L4: pass（安全扫描通过）
- L5: pass（readelf -d libyajl.so 含 SONAME=libyajl.so.2）

## 交付物
- libyajl.so / libyajl_s.a
- json_verify, json_reformat

## 注意事项
- 无标准测试套件
---

**编译结束**: 2026-08-14 16:31
**最终状态**: published
