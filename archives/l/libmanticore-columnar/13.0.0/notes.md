# libmanticore-columnar 13.0.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-03
- 编译器: clang/clang++ (15.0.4)
- 状态: published

## 编译步骤

1. 下载源码：从 GitHub 下载 columnar release-13.0.0 tag
2. 解压源码：libmanticore-columnar-13.0.0.tar.gz
3. 应用补丁：3 个补丁（embeddings 条件判断、knn.cpp vector 处理、SIMDe 支持）
4. 配置 CMake：`cmake -GNinja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_TESTING=OFF ..`
5. 编译：`ninja -j1`
6. 安装（staging）：`DESTDIR=$TEST_PREFIX ninja install`
7. 安装（本地）：`ninja install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Embeddings 库未找到导致安装失败 | CMakeLists.txt 强制安装未找到的库 | 添加条件判断，仅在找到时才安装 |
| 2 | knn.cpp 编译错误：vector 没有 top/pop 方法 | hnswlib searchKnn 返回 vector，不是 priority_queue | 修改 ExtractResults 函数使用 vector 的 back/pop_back |
| 3 | SIMDe 需要从 GitHub 下载 | 网络问题导致 FetchContent 失败 | 支持本地缓存 $HOME/.cache/simde |
| 4 | FastPFORConfig.cmake 路径错误 | 使用 \${CMAKE_CURRENT_LIST_DIR} 导致路径问题 | 改用 ${CMAKE_CURRENT_LIST_DIR} |

## 源码修改

应用了 3 个补丁：

### 0001-knn-CMakeLists.txt.patch
修复 embeddings 库未找到时的安装错误：
- 添加条件判断：`if (EMBEDDINGS_LIB AND NOT EMBEDDINGS_LIB STREQUAL "EMBEDDINGS_LIB-NOTFOUND")`
- 仅在找到 embeddings 库时才创建和安装目标

### 0002-knn-knn.cpp.patch
修复 vector 类型处理：
- hnswlib 的 searchKnn 返回 `std::vector<std::pair<dist_t, labeltype>>`
- 修改 ExtractResults 函数使用 `back()` 和 `pop_back()` 代替 `top()` 和 `pop()`

### 0003-libfastpfor-CMakeLists.txt.patch
支持 HarmonyOS ARM64 架构：
- 添加 SIMDe 支持（HarmonyOS 系统检测）
- 支持本地缓存的 SIMDe（$HOME/.cache/simde）
- 浅克隆减少下载时间
- 修复 FastPFORConfig.cmake 路径引用

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4
- ninja: 1.12.1
- hnswlib: 缓存版本（harmonyos-unknown）
- FastPFOR: 内嵌版本（0.1.9）

## 验证结果

```bash
ls -lh ~/usr/local/share/manticore/modules/
# 输出：
# lib_manticore_columnar.so  23MB
# lib_manticore_knn.so       16MB
# lib_manticore_secondary.so 16MB
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmanticore-columnar-13.0.0-ohos-aarch64.tar.gz | ~55MB | 预编译包（3个共享库模块） |

## 注意事项

1. 这是一个库模块包，不包含可执行文件，无需执行 --version 验证
2. 测试已禁用（BUILD_TESTING=OFF）
3. Embeddings 库未包含，因为编译时未找到该库
4. 使用 DESTDIR 模式安装，符合 R20 铁律
5. 13.0.0 正式版本（非 master 分支的开发版本 0.0.0）
---

**编译结束**: 2026-06-03 11:14
**最终状态**: built
