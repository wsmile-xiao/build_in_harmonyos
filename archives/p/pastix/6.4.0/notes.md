# PaStiX 6.4.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-04
- 编译器: clang（OHOS SDK 26.0.0.18）+ flang-ohos/20.1.0（Fortran 前端, tool_requires）
- 目标: OHOS aarch64（HarmonyOS PC 2in1 真机）
- 状态: built

## 上游测试申报表（R51 清点）

清点方式：配置完成的构建树内 `ctest -N`（注册数=权威），源码目录逐数交叉核对。

| 套件 | 源码位置 | 注册用例数 |
|------|----------|-----------|
| example 示例矩阵（18 个 C 示例 × 4 精度 × 分解/调度/压缩参数组合，shm 单机模式） | `example/CTestLists.txt`（40 条 add_test 模板展开） | 1781 |
| PaStiX 库 bcsc 单元测试（spmv/norm） | `test/CMakeLists.txt` | 27 |
| Fortran 包装示例（fsimple / fmultilap×(seq,mt) / fstep-by-step / fmultidof / flaplacian / fusermat_csr） | `wrappers/fortran90/examples/*.F90` | 7 |
| **合计（ctest -N 实测）** | | **1815** |

- 实运行: **1815**（`conanfile.py` build() 内真实执行 `ctest --output-on-failure -j8`，真机 native）
- 实测结果: **1815/1815 = 100%**（0 failed；独立复跑 60.05 s @ -j8 一致）
- 未运行项: 无。`spm/tests/` 与 `pastix-6.4.0/test/matrix/` 下的测试源码在本次配置中未注册为 ctest 用例（上游 CMake 依开关条件注册），不计入注册数。

## 编译步骤

1. 依赖矩阵（ohpcd 制品仓）：`openblas/0.3.34`、`scotch/7.0.12`、`hwloc/2.14.0`，跨链 zlib 收敛为 `zlib/1.3.1.1`（override）；Fortran 前端 `flang-ohos/20.1.0`（tool_requires，full_mode）。
2. `conanfile.py` generate()：
   - 关闭 `find_package_prefer_config`（恢复 morse Find 模块优先）；
   - 生成可重定位 `hwloc.pc` shim（FindHWLOC 唯一入口）；
   - 注入 flang 三件套（`--target/--sysroot/-resource-dir`）+ 链接 `-L<SDK>/llvm/lib/aarch64-linux-ohos`；
   - 显式给 BLAS/CBLAS/LAPACK/LAPACKE/SCOTCH 的 INCDIR/LIBDIR，全部并入 `CMAKE_PREFIX_PATH`。
3. build()：configure 后硬校验（CBLAS_WORKS / LAPACKE_WORKS / HWLOC_WORKS / SCOTCH_Num_4 / BLAS 库身份指向本包 openblas / config.h 宏面），`make -j16`，随后真机跑全量 ctest。
4. package()：install 面自检（libpastix.a / libpastix_kernels.a / libspm.a / include/pastix.h）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | **1536/1815 用例段错误**（压缩族 `-i` 多参数用例全崩；单 `-i` 对用例却过） | OHOS libc 的 `getopt_long` 置换非选项参数；上游 `common/get_options.c` 用 `argv[optind]` 直读 `-i/-d` 的值而不推进 optind，第二对起读到的都是第一对的值 token（如 `iparm_compress_min_width 16` 后续每对都读 "16"），把 `iparm_compress_when=16` 当合法枚举 → 表头打印索引越界 `compmeth_shnames[16]` → 段错误。设备无 gdb（ptrace 被拒）、无 core dump，用自写 libc 探针程序（同 GETOPT_STRING 复现上游用法）在真机拿到置换语义逐帧证据后定根因 | 补丁 `0001-get-options-consume-value-token.patch`：读到值后 `optind += 1` 显式消费值 token（glibc/OHOS 两种语义下都正确） |
| 2 | Fortran 语言为 project() 必需，设备无 Fortran 编译器 | 上游即使不开 STARPU/PARSEC 仍编译 Fortran 包装源 | `tool_requires("flang-ohos/20.1.0", package_id_mode="full_mode")`；flang 须全参调用（--target/--sysroot/-resource-dir），链接 `-L<SDK>/llvm/lib/aarch64-linux-ohos`（libunwind.a） |
| 3 | find_package(SCOTCH) 绕过 FindSCOTCH，SCOTCH_Num 位宽探测误报 | Conan 工具链默认 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`，命中 config 模式 | generate() 内 `self.conf.define(..., find_package_prefer_config, False)` |
| 4 | FindHWLOC 走 pkg-config 失败 | 依赖包内 hwloc.pc 是构建机残留（prefix=/；Requires.private 指向缺失的 libxml-2.0.pc） | 自写 hwloc.pc shim：prefix 指向实际包目录，Libs 行携带静态闭包 `-lhwloc -lxml2 -lm -lpthread -ldl` |
| 5 | scotch 钉 zlib/1.3.1 与 hwloc/cairo 链钉 zlib/1.3.1.1 冲突 | 同图两版本 zlib 无法共存 | `self.requires("zlib/1.3.1.1", override=True)`（两版本 OHOS 二进制 package_id 一致，`6b129b06...`） |
| 6 | `self.run(env=...)` 传 dict 报 `env argument ... should be a list`（build 完成 100% 后才炸在 ctest 调用） | Conan 2 口径：env 须为 KEY=VALUE **列表** | `env=["OPENBLAS_NUM_THREADS=1", "OMP_NUM_THREADS=1"]`，同时规避 ctest -j8 下 BLAS 线程超卖 |
| 7 | 消费者 E2E 用例 x0 校验「失败」（残差 1.2e-03 却前向 3.3e11，rc=255）；上游 example 二进制同参数 `-c 2` 也 rc=255 | **测试矩阵设计缺陷（非移植问题）**：Laplacian 驱动缺省 alpha=1 生成 `M = D − A` 图 Laplacian，常数向量在零空间 → 矩阵奇异；右端相容时 LU 照常成功、残差机器精度，但解只确定到「相差任意常数」，与 x0 逐位比对必然失配（差值逐次运行漂移）。上游全部注册用例显式给 alpha=2（`s:10:10:10:2`）规避 | 消费者用例 driver 串 `d:30:30` → `d:30:30:1:2`（显式 alpha=2，与上游口径一致）；对照实验：上游自带 `simple_solve_and_refine`/`step-by-step` 在 `d:30:30 -c 2` 下同为 rc=255、改 `d:30:30:1:2` 后 rc=0，证明与 OHOS 移植面无关 |

## 源码修改

- `patches/0001-get-options-consume-value-token.patch`（portability）：
  `common/get_options.c` 两处（`-i` / `-d` 分支）在读取值 token 后补 `optind += 1;`，
  并附注释说明不可依赖 getopt_long 的非置换行为。仅动这一文件，上游其余源码逐字节未改。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| openblas | 0.3.34 | CBLAS/LAPACK/LAPACKE 单一提供者（BLAS 身份经 configure 契约校验） |
| scotch | 7.0.12 | 图剖分（int32 构建，与 PASTIX_INT64=OFF 匹配） |
| hwloc | 2.14.0 | 拓扑/亲和（上游可选依赖，本包显式启用） |
| zlib | 1.3.1.1 | override 收敛（scotch 与 hwloc 链的跨版本冲突） |
| flang-ohos | 20.1.0 | tool_requires（构建期 Fortran 前端） |

## 验证结果

```bash
# 官方 verify（真机）：
$ python3 scripts/ohc-run.py conan-verify pastix 6.4.0
# → G0-G4 全 PASS（Verdict: PASS，2026-10-04T10:54:54）；L2/L4/L5 按脚本逻辑跳过
#   （G4 报"无法找到程序包 ID"为平台 verifier 与 Conan 2 list 输出结构的已知解析差异）
# 真机（HarmonyOS PC 2in1, aarch64），裸 conan create：
$ conan create archives/p/pastix/6.4.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable
...
# build() 内 ctest 实测：
100% tests passed, 0 tests failed out of 1815
Total Test time (real) =  60.05 sec
# test_package 两执行器（消费者视角，真机运行）：
test_pastix_solve:    10 项 CHECK 全过 -> TEST SUMMARY: 10 checks, 0 failed -> ALL PASS
test_pastix_contract: 16 项 CHECK 全过 -> TEST SUMMARY: 16 checks, 0 failed -> ALL PASS
# 消费者用例 x0 校验对照（问题 7；driver 串 alpha 显式化前后）：
driver "d:30:30"      -> 10 checks, 1 failed（前向行 3.29e11 FAILED，rc=255）
driver "d:30:30:1:2"  -> 10 checks, 0 failed -> ALL PASS
```

## 注意事项

- OHOS libc 走 musl 语义，`getopt_long` 会置换 argv 中的非选项参数；凡「读 argv[optind] 却不推进 optind」的用法在 OHOS 上都不可移植（本包补丁即此通用模式）。
- 真机 gdb/lldb 不可用（ptrace 拒绝）、无 core dump；底层库行为取证用「设备原生编译探针程序」路线。
- `make -j` 在真机上打印 `jobserver mkfifo ... Operation not permitted` 属环境噪音（不影响构建完成与依赖正确性）。
- 段错误类问题定根因前不要动上游 CMake 开关面——本包第一嫌疑先落在参数解析（libc 行为差异），事后证明正确。
