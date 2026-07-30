# PETSc 3.25.3 适配笔记

## 编译环境

- 构建系统: PETSc Python configure + make
- 编译日期: 2026-07-17
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
python3 ./configure \
  --prefix=$DEFAULT_PREFIX \
  --with-cc=clang \
  --with-cxx=clang++ \
  --with-fc=0 \
  --with-mpi=0 \
  --with-shared-libraries=0 \
  --with-debugging=0 \
  --download-f2cblaslapack=1 \
  COPTFLAGS='-fPIC -O2' \
  CXXOPTFLAGS='-fPIC -O2'

make PETSC_DIR=$BUILD_SRC_DIR PETSC_ARCH=arch-ohos-c-opt all
make PETSC_DIR=$BUILD_SRC_DIR PETSC_ARCH=arch-ohos-c-opt install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OpenBLAS/OpenMPI 未形成可验证 Conan 依赖 | 下游依赖尚未发布，直接依赖会违反 R36 | PETSc 先做串行自包含版本，使用 `--with-mpi=0` 和 `--download-f2cblaslapack=1` |
| 2 | 自动 conan-init 生成 autotools 模板不适合 PETSc | PETSc 使用 Python configure，不是标准 autotools | 改写 conanfile.py，显式在 source_folder 中运行 `python3 ./configure` |
| 3 | 初次 conan-verify 找不到 `./configure` | Conan build cwd 不是源码根目录 | `self.run(..., cwd=self.source_folder)` |

## 源码修改

无源码补丁。

## 依赖版本

- PETSc 自带 MPIUNI (`--with-mpi=0`)
- PETSc 下载 f2cblaslapack (`--download-f2cblaslapack=1`)

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify petsc 3.25.3
# PASS

python3 scripts/ohc-run.py finish petsc 3.25.3 built
# W3 local CI simulation PASS; archive cleanup still reports non-blocking warnings
```

## 注意事项

- 当前适配是串行静态 PETSc，不启用 OpenMPI。
- Conan 配方按 `build_type` 区分编译参数：Debug 使用 `--with-debugging=1` 和 `-g -O0`，非 Debug 使用 `--with-debugging=0` 和 `-O2`。
- `test_package/test.c` 实质调用 PETSc Vec API，并检查范数结果。
- 通用 `clean-verify` 对 PETSc 会走默认 configure 参数，不代表 Conan 配方失败；以 `conan-verify` 和 W3 本地 CI 为准。
---

**编译结束**: 2026-07-17 14:41
**最终状态**: built
