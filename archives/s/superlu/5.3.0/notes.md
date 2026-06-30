# superlu 5.3.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-22
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

1. 从 GitHub 下载源码包：https://github.com/xiaoyeli/superlu/archive/refs/tags/v5.3.0.tar.gz
2. 解压源码并初始化编译环境：`ohc-run.py init-build superlu 5.3.0`
3. 修复 CMakeLists.txt 中的 cmake_minimum_required 版本（从 2.8.12 更新到 3.5）
4. 创建 build 目录并配置：`cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -Denable_internal_blaslib=YES -DXSDK_ENABLE_Fortran=OFF`
5. 编译：`make -j2`
6. 安装到 staging：`make install DESTDIR=/storage/Users/currentUser/test-install-superlu-5.3.0`
7. 运行测试：`make test`（24 个测试全部通过）
8. 安装到本地：`make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 版本兼容性失败 | CMakeLists.txt 使用旧版本 2.8.12，当前 CMake 4.1.2 不支持 | 更新 cmake_minimum_required 到 3.5 |
| 2 | Fortran 编译器缺失 | CMake 尝试启用 Fortran 支持 | 添加 -DXSDK_ENABLE_Fortran=OFF 禁用 Fortran |
| 3 | 编译警告：deprecated function prototypes | 代码使用 K&R 风格函数声明 | 保留原代码（不影响功能） |

## 源码修改

修改文件：CMakeLists.txt
修改内容：更新 cmake_minimum_required VERSION 从 2.8.12 到 3.5
原因：当前 CMake 4.1.2 不支持低于 3.5 的版本

## 依赖版本

- CMake: 4.1.2
- Clang: 15.0.4
- 内部 BLAS 库：CBLAS（SuperLU 内置）

## 验证结果

```bash
make test
# 输出：
100% tests passed, 0 tests failed out of 24
Total Test time (real) =   0.86 sec

# 测试覆盖：
- s_test: 6 个测试全部通过
- d_test: 6 个测试全部通过
- c_test: 6 个测试全部通过
- z_test: 6 个测试全部通过
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libsuperlu.a | ~1.5 MB | SuperLU 核心静态库 |
| libblas.a | ~200 KB | 内置 CBLAS 库 |
| superlu-5.3.0-ohos-aarch64.tar.gz | ~2.5 MB | 预编译包 |

## 注意事项

1. SuperLU 默认编译为静态库（libsuperlu.a）
2. 使用内置 CBLAS 实现（性能较低，如需高性能应链接外部 BLAS）
3. 编译时需禁用 Fortran 支持（-DXSDK_ENABLE_Fortran=OFF）
4. 源码包含旧的 K&R 风格代码，会产生编译警告但不影响功能
---

**编译结束**: 2026-05-22 18:23
**最终状态**: built
