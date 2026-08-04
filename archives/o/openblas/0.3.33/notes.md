# openblas 0.3.33 编译笔记（HarmonyOS PC · Makefile · NOFORTRAN=1）

## 定位
- 优化 BLAS + f2c 转换版 LAPACK/LAPACKE（NOFORTRAN=1 自动置 C_LAPACK=1）。
- 设备原生 conan 配方，不依赖 Fortran 工具链（本机无 flang；flang-ohos/20.1.0 本地缓存无、ohpcd 404）。
- 与 0.3.34/0.3.28（真 Fortran LAPACK + flang-ohos/20.1.0）方案差异见文末「LAPACK 方案对比」。

## 关键适配
- **构建系统**：makefile（TARGET=ARMV8 BINARY=64 NOFORTRAN=1 NO_SHARED=0 NO_AFFINITY=1）。
- **官方变量复核**：`NOFORTRAN` 是官方主变量（Makefile.system:387，置 1 时自动 C_LAPACK=1 + 清空 FEXTRALIB）；
  `NO_FORTRAN` 只是顶层 Makefile 的别名包装（定义 NOFORTRAN=1 + C_LAPACK=1）。用 NOFORTRAN=1，未沿用 NO_FORTRAN。
- **1 个 portability 补丁**：blas_server.c 的 openblas_setaffinity/getaffinity 由通用能力宏
  `HAVE_PTHREAD_SETAFFINITY_NP` 门控（`#if defined(OS_LINUX) && defined(HAVE_PTHREAD_SETAFFINITY_NP)`），
  该宏由 conanfile.py 在构建期做真实编译+链接探测（probe pthread_setaffinity_np 可用性）产生；
  不包含任何平台宏（无 __OHOS__/OHOS）。原因：部分 musl 工具链（如 OHOS）的 libc.so 不导出
  pthread_setaffinity_np/getaffinity_np（仅 libc.a 有），且 blas_server.c 该段不受 NO_AFFINITY
  保护，ld.lld --no-allow-shlib-undefined 会报 undefined reference；探测失败时不编译该段，
  避免链接错误。
- **构建 env**：LD_LIBRARY_PATH = SDK llvm/lib（给 lld 正确 libxml2.so.16）；CC/AR/RANLIB 用设备 hnp；
  PATH 需补 /bin（Makefile.install 用 `install` 命令，设备 PATH 缺 /bin 会 Error 127）。
- **并行度**：-j20（设备 20 核）。jobserver mkfifo 在 hmdfs 上失败（Operation not permitted）仅是警告，make 仍并行。
- **W3 本地 CI 超时**：conan create 本身成功（test_package 5/5），但 build_and_test.sh 强制重建
  （--build=openblas/*，全量约 9-10 分钟）超过 workflow_checks.py 外层硬编码 600s 超时 → W3 本地模拟 TIMEOUT。
  真实 CI（Buildbot 直接跑 build_and_test.sh，无外层 600s、内部 timeout 2700s）不受此限。

## 环境记录
- clang: 15.0.4（/data/service/hnp/bin/clang，Target aarch64-unknown-linux-ohos）
- OHOS: HongMeng Kernel 1.12.0（aarch64）
- TMPDIR: /storage/Users/currentUser/tmp（hmdfs，不支持 mkfifo）
- arch: armv8 / aarch64

## 产物与验证
- lib/libopenblas.so.0（SONAME）+ 实名 .so + .a + 两级版本软链 + 头（cblas.h/openblas_config.h/lapack.h/lapacke.h）
- ELF: ELF64 DYN AArch64；DT_NEEDED=libc.so；SONAME=libopenblas.so.0；无 RPATH/RUNPATH；无构建机绝对路径（.comment 仅 clang 版本串）
- binary-sign-tool 自签：.codesign 段已写入；sign -selfSign 1 成功；verify 子命令不受该工具支持
- test_package（适配后测试，独立于上游测试统计）：1 个可执行文件 test_probe，5 项断言，
  **5/5（100%）通过**：cblas_dgemm=[19,43,22,50]、dgesv_ 解=[0.8,1.4] info=0、
  dpotrf_ L=[2,0;1,2]、LAPACKE_dgesv 解=[0.8,1.4] info=0、openblas_get_config() 含 "0.3.33"

## 上游测试与适配后测试统计（真实数据）

| 测试入口 | 数量 | 结果 |
|---|---:|---:|
| utest（C） | 1650 | **1650/1650 通过**（openblas_utest 128 + openblas_utest_ext 1522，0 failed，0 skipped） |
| ctest / CBLAS（C） | 12 | **12/12 通过**（xscblat1/2/3、xdcblat1/2/3、xccblat1/2/3、xzcblat1/2/3，全部 exit=0） |
| test/ Fortran BLAS（.f 主程序） | 14 | **未执行** |
| lapack-netlib Fortran（INSTALL/BLAS/TESTING/TESTING） | 1243 | **未执行** |

- **可执行的 C 上游测试：1662/1662 通过**（utest 1650 + ctest 12；已在 conan build 流程内真实执行）
- **Fortran 上游测试：1257 项未执行**（test/ 14 + lapack-netlib 1243）
- **未执行原因**：当前 OHOS/aarch64 执行环境没有 gfortran、flang 或 flang-new；
  `flang-ohos/20.1.0` 从 ohpcd 下载返回 HTTP 404（`conan download -r ohpcd` → 404）
- **当前上游完整测试通过率：N/A**（不得将 N/A 改成 100%；未执行测试不得标记为通过）
- **适配后 test_package**：1 个可执行文件，5 项断言，5/5（100%）——独立于上游测试统计，
  不得将 test_package 5/5 冒充上游完整测试通过率
- 上游测试集成方式：conanfile.py `_run_upstream_tests()` 在 conan build 流程内真实构建+执行
  utest/ctest（非手工替代）；发布包 NOFORTRAN=1 保持不变，test-only 逻辑内置

## 补充说明（Fortran 编译器缺失）

本适配使用 `NOFORTRAN=1`，原因是当前 OHOS/aarch64 编译主机没有可用的 Fortran 编译器
及运行时。该配置不影响已验证的 CBLAS、LAPACK C 接口和 LAPACKE 功能。

当前已实际执行并通过：
- utest：1650/1650；
- ctest/CBLAS：12/12；
- test_package：5/5；
- conan create、conan-verify、finish、W3 本地 CI 及 L0/L1/L4/L5。

尚未执行：
- test/ 下 14 个 Fortran BLAS 测试；
- lapack-netlib 下 1243 个 Fortran 测试。

恢复条件：待 OHOS Fortran 编译器及运行时可用后，执行完整的 `make blas-test`、
`make lapack-test`，再更新真实上游测试通过率。

- 许可证：LICENSE + GotoBLAS_00License.txt + lapack-netlib/LICENSE 已打包到包内 licenses/

## 状态
conan create ✅ / conan-verify ✅（G1-G4、L2/L4/L5）/ test_package 5/5 ✅ / W3 本地 CI 模拟 ✅（外层 timeout=3300s）/ finish ✅（EXIT_CODE=0，.ci-result.json exit_code=0 真实生成）/ 上游测试集成到 conan build 流程（utest 128+1522、ctest 12 全通过；Fortran 测试因无编译器真实跳过）

## LAPACK 方案对比
| 维度 | 本轮 0.3.33（NOFORTRAN=1） | 0.3.34/0.3.28（NOFORTRAN=0 + flang） |
|---|---|---|
| LAPACK | f2c 转换版（C_LAPACK=1） | 真 Fortran（flang-ohos/20.1.0 设备原生编） |
| 依赖 | 无 Fortran 工具链 | flang-ohos/20.1.0（需先发布） |
| 符号量 | 约 7096 个 T | 约 7514 个 T |
| 本轮验证 | ✅ 构建+5 项断言 | 无法验证（flang 不可用） |
---

**编译结束**: 2026-08-01 20:59
**最终状态**: built
