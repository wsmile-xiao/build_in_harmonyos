# libccp4 8.0.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-15
- 编译器: clang 15.0.4 (OHOS SDK)
- 状态: published

## 编译步骤

```bash
# 使用 CMake 构建（上游同时提供 autotools 与 CMake，CMake 为主构建系统）
cmake .. -DFORTRAN_LIB=OFF -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_C_COMPILER=clang
make -j4
make install DESTDIR=$TEST_PREFIX
```

- 产物: `libccp4c.so`（ccp4c C 核心库）、头文件至 `include/ccp4/`、`ccp4c.pc`、`ccp4-config.cmake`、data 文件（atomsf.lib/syminfo.lib/symop.lib 等）安装至 `lib/data/`
- 配置选项: `FORTRAN_LIB=OFF`（见下）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake Error: "Compatibility with CMake < 3.5 has been removed" | CMake 4.x 移除了 cmake_minimum_required < 3.5 的兼容模式；上游 CMakeLists.txt 声明 `cmake_minimum_required(VERSION 3.4)` | 补丁将版本提升至 3.5（知识 E103 bump-cmake-minimum-version，比 E187 CMAKE_POLICY_VERSION_MINIMUM 更可靠） |
| 2 | CMake Error: "No CMAKE_Fortran_COMPILER could be found" | `project(libccp4 C Fortran)` 声明 Fortran 语言后，CMake 在 project() 阶段即强制查找 Fortran 编译器，与 FORTRAN_LIB=OFF 选项无关 | 补丁从 project() 语言列表移除 Fortran（仅保留 C）；FORTRAN_LIB=OFF 同时关闭 ccp4f 构建 |
| 3 | ccp4f 依赖 mmdb2 未发布 | CMakeLists.txt 中 `find_library(MMDB2 mmdb2)` FATAL_ERROR；mmdb2 未适配发布，OHOS 无 Fortran 编译器 | 方案 A 关闭 FORTRAN_LIB：下游 libpdb-redo 只依赖 ccp4c（C 库），源码无任何 ccp4f 引用，功能损失面仅 Fortran 接口库 |
| 4 | test_package 5 项 FAIL（frac_orth_mat volume=0） | `ccp4uc_frac_orth_mat` 的 ncode 有效值为 1–6（switch 无 case 0），ncode=0 时 ro 矩阵全零 | 测试改用 ncode=1 |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`：
  - `cmake_minimum_required(VERSION 3.4)` → `3.5`（CMake 4.x 兼容）
  - `project(libccp4 C Fortran)` → `project(libccp4 C)`（移除 Fortran 语言声明）

## 依赖版本

- 无外部依赖（ccp4c 为纯 C 库，零 requires）

## 验证结果

```bash
# conan-verify 8 道门禁全通过（G0-G4 + L2/L4/L5）
python3 ohc-run.py conan-verify libccp4 8.0.0
# test_package 14 项断言全部 PASS（ccp4uc_calc_rcell/frac_orth_mat/orth_to_frac/frac_to_orth/liberr_verbosity/strerror）
```

上游测试情况：CMake 构建无测试目标（无 enable_testing/add_test，configure.ac 亦无），仓库内仅 `fortran/testlib.f`（Fortran 机器相关例程测试，属 ccp4f/FORTRAN_LIB 部分，本适配关闭该部分）。自研 test_package 14 项断言补齐核心功能覆盖（倒格子计算、正交化矩阵、坐标正反变换 roundtrip、错误处理 API）。

## 注意事项

- 上游源：GitHub 镜像 `ndevenish/libccp4`（CCP4 bzr 官方仓库自动镜像，v8.0.0 tag 与 GitLab 官方 commit 65f58303 内容逐字节一致，diff=0 实测确认）；官方仓库 https://gitlab.com/CCP4/libccp4
- license: LGPL-3.0（COPYING 为 GPL-3.0 主文本，COPYING.LESSER 为 LGPL-3.0）
- ccp4-config.cmake（find-module）随包安装，供下游 `find_package(CCP4 COMPONENTS ...)` 使用，配方通过 `cpp_info.builddirs = ["lib/cmake/ccp4"]` 暴露
- pkg-config 元数据 `ccp4c.pc` 随包安装
---

**编译结束**: 2026-09-15 20:19
**最终状态**: published
