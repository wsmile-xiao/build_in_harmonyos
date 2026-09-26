# simbody 3.8 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-24
- 编译器: clang/clang++ (15.0.4, aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 本地探索编译（build-ohos 目录）
cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DBUILD_EXAMPLES=ON \
  -DBUILD_VISUALIZER=OFF -DINSTALL_DOCS=OFF \
  "-DBUILD_USING_OTHER_LAPACK=<lapack包内 liblapack.a;libblas.a;libFortranRuntime.a;libFortranDecimal.a>" \
  -DCMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG=-Wl,-soname, \
  -DCMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
export LD_LIBRARY_PATH=<build-ohos>
ctest -j$(nproc)   # 113/113 PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `No INSTALL_DESTINATION given to CONFIGURE_PACKAGE_CONFIG_FILE()` | OHOS 下 CMake 无 Platform/HarmonyOS 模块，`if(UNIX)` 分支不生效，SIMBODY_CMAKE_DIR 为空 | CMakeLists.txt 改 `if(UNIX OR CMAKE_SYSTEM_NAME MATCHES "OHOS\|HarmonyOS")`（0001 补丁） |
| 2 | 测试运行时 `Error loading shared library ../libSimTKmath.so` | 未知平台下 CMake 未注入 -soname，DT_NEEDED 记录相对路径 | 配方 generate() 设 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG/_C_FLAG=-Wl,-soname,` |
| 3 | TestNiceTypeName FAIL：`std::vector<int>` 期望 `std::vector<int,std::allocator<int>>` | OHOS clang15/libc++ 的 ABI 内联命名空间是 `__n1`，typeid 反解出 `std::__n1::vector`，规范化只剥离 `__1` | NiceTypeName.cpp 增加 `\b__n[0-9]+::` 剥离（0002 补丁） |
| 4 | 链接 lapack/blas 报 `undefined reference to _FortranAio*` | 制品仓 lapack 为 flang 编译，静态库引用 flang Fortran 运行时符号 | BUILD_USING_OTHER_LAPACK 一并链接 libFortranRuntime.a/libFortranDecimal.a |

## 源码修改

- patches/0001-CMakeLists.txt.patch — OHOS/HarmonyOS 平台按 UNIX 处理（REALTIME/PTHREAD/MATH/DL 库与 SIMBODY_CMAKE_DIR）
- patches/0002-SimTKcommon-src-NiceTypeName.cpp.patch — 类型名规范化剥离 libc++ ABI 命名空间 `__n1`

## 依赖版本

- lapack/3.12.1（含 liblapack.a/libblas.a/libFortranRuntime.a/libFortranDecimal.a，制品仓已发布）

## 验证结果

```bash
ctest -j$(nproc)          # 113/113 PASS（上游双口径台账见 reports/upstream-test-ledger.md）
./TestOHOSPendulum        # HarmonyOS 专项测试 PASS（实测周期 2.020s vs 解析 2.007s）
conan create ... -pr:h=ci/conan/profiles/ohos-aarch64   # G0-G4/L2/L4/L5 全通过
test_package test_simbody # 1/1 Passed
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（shared 选项、SONAME 标志、lapack 依赖） |
| conandata.yml | 官方 GitHub tag 源 + sha256 + 2 补丁登记 |
| patches/0001, 0002 | OHOS 平台适配补丁 |
| test_package/ | 消费者测试（公开 API 单摆周期验证） |
| knowledge/drafts/DRAFT-simbody-3.8-libcxx-n1-typeid-canonicalize.kv/.md | 路径 B 知识草稿 |

## 注意事项

- 上游测试统计必须用双口径台账（source_declared_total=113 / executed_passed=113），以官方 tag 源码枚举为准。
- 共享库需显式 SONAME 标志，否则 DT_NEEDED 用相对路径导致下游加载失败（E207/E330/E383 同族）。
- 知识路径 B：libc++ ABI 命名空间 `__n1` 类型名规范化（E247 场景不同，为新增差异）。

---

**编译结束**: 2026-09-24
**最终状态**: built
