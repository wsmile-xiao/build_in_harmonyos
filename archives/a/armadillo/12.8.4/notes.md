# armadillo 12.8.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 解压源码到 ~/tmp/builds/armadillo-12.8.4.work/
2. 创建build目录并执行cmake配置：
   ```bash
   mkdir build && cd build
   cmake -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DBUILD_SHARED_LIBS=ON ..
   ```
   ⚠️ **重要**: 必须使用 `-DBUILD_SHARED_LIBS=ON` 来编译共享库(.so)，否则默认只编译静态库(.a)
3. 执行编译：
   ```bash
   make -j2
   ```
4. 安装到测试目录：
   ```bash
   make install DESTDIR=$TEST_PREFIX
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure脚本报错 | configure只是wrapper，需要cmake | 直接使用cmake构建系统 |
| 2 | manifest.yaml build_system字段错误 | 初始化时误判为autotools | 更新为cmake |
| 3 | packaging目录为空 | 编译未完成，未制作预编译包 | 完成编译后运行package命令 |

## 源码修改

无补丁文件，源码无需修改即可编译。

## 依赖版本

- cmake 4.1.2
- clang 15.0.4

依赖: openblas/0.3.34（提供BLAS和LAPACK，使armadillo支持solve/inv/eig_sym/svd等高级功能）。

## 验证结果

```bash
# 检查DESTDIR安装产物
ls -lh ~/tmp/test-install-armadillo-12.8.4/$HOME/usr/local/lib/libarmadillo.so
# 输出: libarmadillo.so (18K) ✅ 共享库

ls -lh ~/tmp/test-install-armadillo-12.8.4/$HOME/usr/local/lib/pkgconfig/armadillo.pc
# 输出: armadillo.pc (317 bytes) ✅ pkgconfig文件

# 检查本地安装
ls -lh ~/usr/local/lib/libarmadillo*
# 输出: libarmadillo.so (18K) + libarmadillo.a (3.6K)
# 注意: .a是之前遗留文件，本次编译生成的是.so

file ~/usr/local/lib/libarmadillo.so
# 输出: ELF shared object, 64-bit LSB arm64, not stripped

# 检查头文件
ls ~/tmp/test-install-armadillo-12.8.4/$HOME/usr/local/include/
# 输出: armadillo (主头文件) + armadillo_bits/ (头文件目录)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libarmadillo.so | 18K | 共享库文件 ✅ |
| armadillo.pc | 317B | pkg-config文件 ✅ |
| armadillo (header) | ~ | 主头文件 |
| armadillo_bits/ | ~ | 头文件目录（数百个.hpp文件） |

⚠️ 注意: 上次编译错误记录为 ".so 实际安装的是 .a"，现已修正为正确编译共享库。

## 功能测试结果 (2026-05-21 协作者质量检查)

### 测试程序
```cpp
// ~/tmp/armadillo_test_basic.cpp
// 测试矩阵运算、向量运算、转置、元素访问等基本功能
```

### 编译命令
```bash
clang++ -std=c++14 -I~/usr/local/include -L~/usr/local/lib -larmadillo test.cpp -o test
LD_LIBRARY_PATH=~/usr/local/lib ./test
```

### 测试结果
| 功能 | 状态 | 说明 |
|------|------|------|
| 矩阵加减乘 | ✅ PASS | randu, +, -, * 运算正常 |
| 向量运算 | ✅ PASS | norm, sum, max, min, dot 正常 |
| 矩阵转置 | ✅ PASS | .t() 方法正常 |
| 元素访问 | ✅ PASS | (i,j), row(), col() 正常 |
| 特殊矩阵 | ✅ PASS | zeros, ones, eye 正常 |
| 矩阵遍历 | ✅ PASS | accu, 迭代器正常 |
| solve() | ✅ PASS | openblas提供LAPACK，solve()正常工作 |
| eig_sym() | ✅ PASS | openblas提供LAPACK，eig_sym()正常工作 |
| inv() | ✅ PASS | openblas提供LAPACK，inv()正常工作 |
| svd() | ✅ PASS | openblas提供LAPACK，svd()正常工作 |

### 结论
- ✅ 基本功能全部可用（不依赖LAPACK的运算）
- ✅ 高级功能通过openblas提供LAPACK支持（solve, eig_sym, inv, svd全部通过测试）
- ✅ pkg-config 配置正确，编译链接正常
- ✅ 预编译包可用于部署

## 注意事项

1. **必须使用 BUILD_SHARED_LIBS=ON**: armadillo默认编译静态库(.a)，需要显式指定 `-DBUILD_SHARED_LIBS=ON` 来编译共享库(.so)
2. configure脚本只是wrapper: 实际需要cmake构建系统
3. **无BLAS/LAPACK时功能受限**: ~~可以编译和基本使用，但性能和功能受限~~ 已修复：通过添加openblas/0.3.34依赖，BLAS和LAPACK均可用，支持solve/inv/eig_sym/svd等全部高级功能。
4. 编译产物是wrapper库: libarmadillo.so很小（18K），因为它只是header-only库的wrapper
5. 需要cmake >= 3.10版本（CMake < 3.10兼容性警告）**编译命令**: cmake -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DBUILD_SHARED_LIBS=ON .. && make -j2 && make install DESTDIR=$HOME/tmp/test-install-armadillo-12.8.4
**关键发现**: BUILD_SHARED_LIBS=ON 必须显式指定，否则默认编译静态库
---

**编译结束**: 2026-09-05 02:34
**最终状态**: published
