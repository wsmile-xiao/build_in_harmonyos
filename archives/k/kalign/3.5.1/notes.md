# kalign 3.5.1 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-08-12
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
mkdir build && cd build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DUSE_OPENMP=OFF \
  -DENABLE_SSE=OFF \
  -DENABLE_AVX=OFF \
  -DENABLE_AVX2=OFF \
  -DBUILD_PYTHON_MODULE=OFF \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_BUILD_TYPE=Release
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake check_c_source_runs 失败 | 鸿蒙交叉编译环境无法运行 test 二进制 | 禁用 ENABLE_SSE/AVX/AVX2 |
| 2 | OpenMP 检测失败 | 鸿蒙 clang 无 libomp | USE_OPENMP=OFF |
| 3 | 共享库配置下 ctest 的 C++Lib/DSSIM 失败 | 测试二进制 NEEDED 为相对路径 `../lib/libkalign.so`，ctest 工作目录(源码 tests/)下解析不到共享库 | 使用与配方一致的静态构建（BUILD_SHARED_LIBS=OFF），15/15 全部通过 |

## 验证结果

```bash
$ kalign --version
kalign 3.5.1

$ ctest
100% tests passed, 0 tests failed out of 15
```

## 依赖

- 无外部 C 库依赖（仅 C 编译器 + CMake + pthreads）

## 产物

- `bin/kalign` — 命令行多序列比对工具
- `lib/libkalign.a` — 静态库
- `include/kalign/kalign.h` — 公共头文件
---

**编译结束**: 2026-08-12 19:17
**最终状态**: built
