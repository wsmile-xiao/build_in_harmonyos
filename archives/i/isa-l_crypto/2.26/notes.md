# isa-l_crypto 2.26 适配笔记

## 编译环境
- 构建系统: cmake（原计划 autotools，因缺少 automake 切换为 cmake）
- 编译日期: 2026-04-24
- 编译器: clang (LLVM)
- 状态: partial

## 编译步骤
1. 下载源码：https://api.github.com/repos/intel/isa-l_crypto/tarball/refs/tags/v2.26
2. 原计划使用 autotools，因缺少 automake/aclocal 导致 autogen.sh 失败
3. 切换到 CMake 构建
4. 配置：`cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DBUILD_TESTS=OFF -DBUILD_PERF=OFF -DSAFE_DATA=ON -DSAFE_PARAM=ON`
5. 编译：`cmake --build . -j$(nproc)`
6. 安装：`DESTDIR=$STAGING cmake --install .`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autogen.sh 失败 | 缺少 automake/aclocal | 切换到 CMake 构建 |
| 2 | 部分测试编译失败 | 缺少 OpenSSL 头文件 | 禁用 BUILD_TESTS 和 BUILD_PERF |
| 3 | aarch64 无汇编优化 | ISA-L 针对 x86 SIMD 设计 | 使用 base C 实现 |

## 依赖版本
- cmake
- clang

## 验证结果
编译成功。libisal_crypto.so (118KB)。打包大小 350.1KB。

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| isa-l_crypto-2.26-ohos-aarch64.tar.gz | 304KB | 预编译包 |

## 注意事项
- aarch64 版本使用 C 基础实现，无 SIMD 性能优化
- v2.26 tag 名称不带 .0 后缀
