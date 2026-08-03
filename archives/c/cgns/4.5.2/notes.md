# cgns 4.5.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-31
- 编译器: clang/clang++ 15.0.4 (aarch64-linux-ohos)
- 状态: built

## 编译步骤
```bash
conan create archives/c/cgns/4.5.2 \
  --version=4.5.2 --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```
- CMake 配置（CGNS_ENABLE_HDF5=OFF）→ 构建 → package → test_package 全部通过
- 退出码: 0

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 报 System is unknown to cmake | OHOS 不在 CMake 已知平台列表中 | 使用 CMAKE_TOOLCHAIN_FILE 指定 OHOS 交叉编译配置 |
| 2 | HDF5 依赖不可用 | OHOS 环境无 HDF5 库 | 禁用 HDF5 支持（-DCGNS_ENABLE_HDF5=OFF） |
| 3 | Fortran 编译器不可用 | OHOS SDK 无 flang/gfortran | CGNS_ENABLE_FORTRAN 不启用，Fortran 测试 N/A |

## 源码修改
无持久补丁。

## 依赖版本
无外部 Conan 依赖。

## 上游测试核验（临时启用 TESTS 实测）
> 验证方式: 在 OH 编译执行端下载上游源码，临时启用 CGNS_ENABLE_TESTS=ON 实际构建并执行 ctest。

### C 测试（src/tests，CTest 注册）
- 注册数: **24 个**
- 执行: **23 个执行并通过，1 个 test_back_comp skip**（上游 SKIP_RETURN_CODE 125 机制），0 个失败
- **执行通过率: 23/23（100%），另有 1 个 skip**（不写 24/24 通过）
- 命令: `ctest --output-on-failure` → `100% tests passed, 0 tests failed out of 24`，退出码 0

### Fortran 测试（src/tests，CTest 注册）
- 注册数: **10 个**（cgiof_f03/cgwrite_f03/cgread_f03/cgzconn_f03/cgsubreg_f03/test_general_rindf/test_family_treef/test_bboxf/test_complexf/test_particlef）
- 执行结果: **0/10 N/A** — 缺少 Fortran 编译器（flang/gfortran 均不可用），CMake 配置阶段 `The Fortran compiler identification is unknown` 失败

### UserGuide 示例（Test_UserGuideCode，非 CTest 自动化测试）
- C_code: **38 个源文件构建成功**（19 read_* + 19 write_*），**非 CTest 自动化测试**（不注册于 ctest）
- Fortran_code: **36 个源文件，0/36 N/A** — 缺少 Fortran 编译器
- C_code_parallel: **8 个 C 源文件**（read/write_grid_str_parinzone/paroverzone + read/write_flowcentrind_str_parinzone/paroverzone），需 MPI，本环境无 MPI，未执行；**非 CTest 自动化测试**

## 新增测试（test_package）
- 消费者测试: 1 个（6 个 CGNS API 断言）→ **6/6 通过（100%）**
- 断言链: cg_open(CG_MODE_WRITE) → cg_base_write → cg_close → cg_open(CG_MODE_READ) → cg_nbases → cg_close

## 验证结果
```bash
conan create archives/c/cgns/4.5.2 --build=missing   # 退出码 0
conan-verify: G0-G4 + L2/L4/L5 全部 PASS              # 退出码 0
W3 本地 CI: setup.sh + build_and_test.sh 通过          # 退出码 0
.ci-result.json: 有效（exit_code=0, step=W3_local_ci）
test_package: 6/6 断言通过
```

## 注意事项
- finish 退出码非 0 来自已获官方确认的公共框架问题（E213/E214 知识图谱校验 errors 及 ARCHIVE-SPEC v3.0 已废弃的 packaging/.staging-verified 检查），与 cgns 4.5.2 适配无关
- 上游 C 测试不依赖 HDF5 即可完整构建执行（实测 23/23 + 1 skip）；HDF5 仅影响部分 HDF5 专用用例
---

**编译结束**: 2026-07-31 17:22
**最终状态**: published
