# double-conversion 3.4.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-02
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: published

## 编译步骤

1. **下载源码**：从 GitHub 下载 `double-conversion-3.4.0.tar.gz`，sha256 校验通过
2. **CMake 配置**：
   ```bash
   cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
            -DCMAKE_BUILD_TYPE=Release \
            -DBUILD_SHARED_LIBS=ON \
            -DBUILD_TESTING=ON
   ```
3. **编译**：`make -j2` — 成功构建 `libdouble-conversion.so` 及测试程序 `cctest`
4. **安装（Staging 隔离）**：`make install DESTDIR=$TEST_PREFIX`
5. **单元测试**：`ctest` — 9/9 全部通过
6. **Conan 配方生成**：`ohc-run.py conan-init double-conversion 3.4.0`
7. **Conan 配方验证**：`ohc-run.py conan-verify double-conversion 3.4.0` — G0-G4 + L2/L4/L5 全部通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 不认识 HarmonyOS 平台 | CMake 无 HarmonyOS platform module (E092) | 配方自动处理，CMake 仍可正常编译，不影响结果 |
| 2 | 编译器路径配置 | Conan profile 通过 `tools.build:compiler_executables` 指定 clang 路径 | 配方 `generate()` 仅使用 `CMakeToolchain`，编译器路径由 Conan profile 自动注入，无需手动重写 toolchain (R33) |
| 3 | HMDFS build 文件夹冲突 | Bazel BUILD 文件与 CMake build 文件夹大小写冲突 (R21) | `cmake_layout(self, build_folder="_build")` 使用 `_build` 替代默认 `build` |
| 4 | make jobserver mkfifo 失败 | `/tmp` 只读，`mkfifo` 操作不允许 (E002) | 非致命，make 仍正常完成编译，不影响结果 |

## 源码修改

无源码修改。编译过程中未对源码做任何补丁或修改，`patches_applied: []`。

## 依赖版本

无外部依赖。double-conversion 是纯 C++ 库，不依赖任何第三方库，`dependencies: []`。

## 验证结果

### conan-verify 结果（PASS）

```bash
$ python3 "$SKILL_ROOT/scripts/ohc-run.py" conan-verify double-conversion 3.4.0

G0: ✅ PASS  — 预构建风险评估通过，E092 已在配方中处理
G1: ✅ PASS  — 配方完整性检查通过（conanfile.py + conandata.yml + test_package/）
G2: ✅ PASS  — conan create 成功
G3: ✅ PASS  — 系统同名库隔离检查通过（非系统同名库，默认动态链接）
G4: ✅ PASS  — 产物完整性检查通过（1 .so + 12 头文件）
L2: ✅ PASS  — 纯库包，跳过 smoke test
L4: ✅ PASS  — ELF 安全扫描通过
L5: ✅ PASS  — 产物与基线完全一致（20 个文件）
```

### ctest 结果（9/9 通过）

```
Test project .../build
    Start 1: test_bignum          ........   Passed    0.13 sec
    Start 2: test_bignum_dtoa     ........   Passed    0.33 sec
    Start 3: test_conversions     ........   Passed    0.04 sec
    Start 4: test_diy_fp          ........   Passed    0.03 sec
    Start 5: test_dtoa            ........   Passed    0.09 sec
    Start 6: test_fast_dtoa       ........   Passed    0.06 sec
    Start 7: test_fixed_dtoa      ........   Passed    0.05 sec
    Start 8: test_ieee            ........   Passed    0.04 sec
    Start 9: test_strtod          ........   Passed    0.05 sec

100% tests passed, 0 tests failed out of 9
Total Test time (real) =   0.84 sec
```

### test_package 结果（1/1 通过）

```
1/1 Test #1: test_double-conversion ...........   Passed    0.07 sec
100% tests passed, 0 tests failed out of 1
```
---

**编译结束**: 2026-09-04 05:08
**最终状态**: published
