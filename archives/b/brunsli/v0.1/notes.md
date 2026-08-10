# brunsli v0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-29
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

1. 下载源码 tar.gz (GitHub 超时需手动 wget)
2. 下载子模块: brotli v1.0.7, googletest release-1.10.0 (GitHub tar.gz不含子模块)
3. 解压子模块到 third_party/brotli 和 third_party/googletest
4. 修改 CMakeLists.txt: 添加 `include_directories("${CMAKE_CURRENT_SOURCE_DIR}/third_party/brotli/c/include")`
5. cmake 配置: `cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ..`
6. make -j2: 编译成功
7. make install DESTDIR=$TEST_PREFIX: 安装共享库和头文件
8. 手动复制可执行文件(cbrunsli, dbrunsli)和静态库到 staging 目录
9. ctest: 无可用测试

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required(VERSION 3.1) 不兼容 cmake 4.x | cmake 4.x 删除了 <3.5 兼容性 | 传递 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 2 | brotli 子模块目录为空 | GitHub tar.gz 不含 git 子模块内容 | 手动下载 brotli v1.0.7 和 googletest release-1.10.0 解压 |
| 3 | 编译时找不到 brotli/decode.h 头文件 | brotli 的 include_directories() 在子目录 scope，不传播到父级 | 修改 CMakeLists.txt 添加 `include_directories("${CMAKE_CURRENT_SOURCE_DIR}/third_party/brotli/c/include")` |
| 4 | 链接时找不到 -lbrotlidec-static | brotli master 分支不创建 `-static` 变体库 | 使用 brotli v1.0.7（创建 `-static` 库的兼容版本） |
| 5 | 上游 install 仅安装共享库和头文件 | brunsli.cmake 的 install() 只针对共享库 | 手动复制可执行文件和静态库到 staging |

## 源码修改

### CMakeLists.txt
添加了 brotli include_directories 路径（在 add_subdirectory(third_party) 之后）:
```cmake
include_directories("${CMAKE_CURRENT_SOURCE_DIR}/third_party/brotli/c/include")
```

## 依赖版本

- brotli: v1.0.7 (内嵌子模块)
- googletest: release-1.10.0 (内嵌子模块)

## 验证结果

```bash
# 可执行文件验证
./cbrunsli  → "Failed to open input file" (正常，无输入文件时)
./dbrunsli  → "Failed to open input file" (正常，无输入文件时)

# ctest
No tests were found
```

## 交付物

| 文件 | 说明 |
|------|------|
| cbrunsli | JPEG→Brunsli 编码器 |
| dbrunsli | Brunsli→JPEG 解码器 |
| libbrunslidec-c.so | Brunsli 解码共享库 |
| libbrunslienc-c.so | Brunsli 编码共享库 |
| libbrunslicommon-static.a | Brunsli 公共静态库 |
| libbrunslidec-static.a | Brunsli 解码静态库 |
| libbrunslienc-static.a | Brunsli 编码静态库 |
| libbrotlicommon-static.a | Brotli 公共静态库 |
| libbrotlidec-static.a | Brotli 解码静态库 |
| libbrotlienc-static.a | Brotli 编码静态库 |
| include/brunsli/*.h | Brunsli 头文件 |
| include/brotli/*.h | Brotli 头文件 |

## 注意事项

- brunsli v0.1 的 brotli 子模块需要特定版本 (v1.0.7)，不能使用 master 分支
- cmake_minimum_required VERSION 低于 3.5 时需传递 CMAKE_POLICY_VERSION_MINIMUM
---

**编译结束**: 2026-08-05 11:35
**最终状态**: built
