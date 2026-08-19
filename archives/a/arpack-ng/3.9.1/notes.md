# arpack-ng 3.9.1 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-08-13
- 编译器: clang/clang++ (LLVM 15.0.4) + flang (LLVM 20.1.0 via flang-ohos tool_requires)
- 状态: published

## 编译步骤

```bash
# Source the build context
source .build-context-arpack-ng-3.9.1

# Install flang-ohos via conan (provides Fortran compiler)
conan install --requires=flang-ohos/20.1.0

# Configure with CMake
cd $BUILD_SRC_DIR && mkdir -p build-ohos && cd build-ohos
cmake .. \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
  -DCMAKE_Fortran_COMPILER=<flang-ohos>/bin/flang \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DCMAKE_INSTALL_PREFIX=$TEST_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DMPI=OFF \
  -DICB=ON \
  -DEXAMPLES=OFF \
  -DTESTS=ON \
  -DBLAS_LIBRARIES=<openblas>/lib/libopenblas.a \
  -DLAPACK_LIBRARIES=<lapack>/lib/liblapack.a \
  -DCMAKE_EXE_LINKER_FLAGS="--sysroot=<OHOS_SDK>/sysroot"

# Build and install
make -j4
make install

# Run tests
ctest -V
# Result: 100% tests passed, 6 tests passed out of 6
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | flang链接失败：找不到 Scrt1.o/crti.o/crtn.o | flang 不知道 OHOS SDK sysroot 路径 | 设置 CMAKE_EXE_LINKER_FLAGS=--sysroot=<OHOS_SDK>/sysroot |
| 2 | flang链接失败：找不到 libunwind.a | OHOS SDK 的 libunwind 在不同目录 | 需要完整 sysroot 设置（包含 LLVM lib 路径） |
| 3 | 动态链接库运行时找不到 libarpack.so.2 | OHOS 动态链接器不解析 LD_LIBRARY_PATH | 使用静态编译 (BUILD_SHARED_LIBS=OFF) |
| 4 | Fortran runtime (_FortranAio*) 符号未定义 | ld.lld 未从 libFortranRuntime.a 拉入所需对象 | 静态链接时 flang 自动处理；消费方需链接 -lFortranRuntime |
| 5 | check_env.py 脚本崩溃 (NameError: 'e') | automake 权限不足触发异常处理 bug | 修复 check_env.py except 语法 (as exc) |

## 源码修改

无补丁。源码未做任何修改，通过 CMake 选项配置。

## 依赖版本

- openblas/0.3.34 (ohpcd 制品仓)
- lapack/3.12.1 (ohpcd 制品仓)
- flang-ohos/20.1.0 (ohpcd 制品仓, tool_requires, 提供 Fortran 编译器)

## 验证结果

```bash
$ ctest -V
100% tests passed, 0 tests failed out of 6
Total Test time (real) =   0.31 sec
```

测试内容：
- dnsimp_tst: 非对称特征值问题
- bug_1323_tst: 回归测试
- bug_58_double_tst: 回归测试
- bug_79_double_complex_tst: 复数回归测试
- bug_142_tst: 回归测试
- bug_142_gen_tst: 广义特征值回归测试

## 注意事项

1. **静态编译必须**: OHOS 动态链接器不解析 LD_LIBRARY_PATH，共享库无法在运行时被找到。arpack-ng 必须静态编译。
2. **flang-ohos tool_requires**: arpack-ng 是 Fortran 库，需要 flang-ohos 提供 Fortran 编译器。flang-ohos/20.1.0 已在 ohpcd 制品仓。
3. **OHOS sysroot**: flang 需要 `--sysroot` 指向 OHOS SDK sysroot 才能找到 CRT 文件和系统库。
4. **ICB=ON**: 启用 ISO_C_BINDING，提供 C/C++ API 头文件 (arpack.h)，使 test_package 可以用 C 编写测试。
5. **消费方链接**: 使用 libarpack.a 的下游包需要链接 flang-ohos 的 libFortranRuntime.a 和 libFortranDecimal.a。
---

**编译结束**: 2026-08-13 19:02
**最终状态**: built
