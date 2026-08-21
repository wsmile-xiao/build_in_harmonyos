【申请人账号】2301_80739235
【队伍名称】天天开心
【申请日期】2026/07/31
【库名称】scalapack
【版本】2.2.3

## 关联 PR

PR：!5839

PR 链接：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/5839

分支信息：feat/scalapack-2.2.3 -> main

当前状态：open

当前路径：路径 A（基础适配）+ 路径 B（贡献创新）+ 路径 C 候选

## 申请事项

本 Issue 用于申请将 ScaLAPACK 2.2.3 纳入路径 C 高难度挑战候选清单，并记录与 PR #5839 一一对应的技术和测试证据。本申请不是直接申请路径 C 分值；若评审委员会认为证据不足，本任务仍按路径 A + 路径 B 继续评审。高难度理由必须同时说明 Fortran、BLAS/LAPACK 和 MPI 三条边界，且不得用 C-only 或单 rank 证据替代混合语言、多组件和多 rank 验证。

## 高难度分析

ScaLAPACK 2.2.3 不是只编译一个静态库的普通适配：它把 C、Fortran、BLACS、PBLAS、BLAS/LAPACK 数值 ABI、MPI C/Fortran wrapper 与 OHOS arm64 签名和多 rank 测试串成一个跨阶段闭环。路径 C 候选依据如下。

**1. 依赖链庞大、全量测试校验成本极高**

上游构建同时固定 openblas/0.3.34、mpich/5.0.1.2 和 flang-ohos/20.1.0，并注册 100 个 MPI CTest 入口，包含 2 个 BLACS、24 个 PBLAS 和 74 个 LIN/EIG 测试。完整 W3 实际执行 100/100，两个最长特征值测试分别耗时 832.97 秒和 840.37 秒，不能用单个 smoke test 代替。除此之外还要执行 1/1 的 Conan CMakeDeps 消费者测试，确认两 rank 的 BLACS grid、LP64 numroc_ 分布和 failures=0。

**2. 私有编译工具链，现有知识库无法直接适配**

目标使用项目专用的 flang-ohos/20.1.0 C/Fortran 工具链和 OHOS arm64 交叉编译环境。现有知识条目只能分别覆盖 MPI provider 身份或一般 Conan 组件规则，不能直接给出 ScaLAPACK 的 Fortran 模块、BLAS/LAPACK 链接顺序、ExternalProject 禁止下载替代依赖、CMakeDeps headerless 元数据和 OHOS ELF 签名的完整方案，因此需要新增配方级证据和 E2156/E2155 配对知识草稿。

**3. Fortran、BLAS/LAPACK 与 MPI 的混合 ABI 和运行时边界（其他高难维度）**

Fortran 侧必须绑定 Flang runtime，并保持 INTEGER*4；BLAS/LAPACK 侧必须固定 OpenBLAS LP64，验证符号、调用约定和数值结果；MPI 侧必须由同一个 OHOS provider 同时提供 mpicc、mpifort/mpif90、mpiexec、Fortran module 或 mpif.h 以及运行时，并验证 C/Fortran 混合链接和多 rank 行为。三者任一身份或整数宽度漂移都会产生可编译但不可运行或数值错误的包，不能用全 i8、C-only MPI 或单 rank smoke 掩盖。

## 申请原因

1. Fortran 与 C 混合构建要求 flang-ohos/20.1.0 的编译器、Fortran module 和 runtime 与同一 MPICH provider 的 mpifort/mpif90、mpif.h 或等价模块保持一致；这不是普通 CMake 库的单语言编译。
2. BLAS/LAPACK 数值 ABI 必须明确绑定 openblas/0.3.34 的 LP64 和 Fortran INTEGER*4，检查 BLAS/LAPACK 只解析到目标 OpenBLAS，避免隐式链接主机库或发生整数宽度错配。
3. MPI 必须同时满足 C wrapper、Fortran wrapper/module/runtime、mpiexec 多 rank 启动和干净退出；ScaLAPACK 的 BLACS/PBLAS 测试不能由 C-only MPI 或单 rank 结果替代。
4. 上游 100 项 CTest 和独立 1 项消费者测试需要完整执行，且每个可加载 ELF 都要经过 OHOS 签名和重定位验证，执行成本和失败诊断边界明显高于普通单库适配。

## 知识库查重情况

- 查重范围：knowledge/graph、knowledge/drafts、knowledge/doc、knowledge/operations。
- 检索词：ScaLAPACK、Fortran、BLAS、LAPACK、MPI、BLACS、BLACS_GRIDEXIT、TESTSTRING、MPI_Abort、CMakeDeps、includedirs、headerless library。
- 查重结论：未找到同时覆盖 BLACS 原目录 RUNPATH、空 CMake list 参数、MPI_Abort 前 Fortran stdout flush 和 headerless Conan imported target 的等价正式知识；E221、E216、E217、E242 仅为相邻模式。
- 本 PR 提交 E2156-draft-2301.kv/.md 与 E2155-draft-2301.kv/.md 配对草稿，KV 均含 draft: true，不修改正式 graph/doc/index。

## 可复用说明

1. 对 ScaLAPACK、Global Arrays、NWChem 等同时消费 C 与 Fortran MPI 的 HPC 软件，必须绑定同一 provider 的 mpicc、mpifort/mpif90、module/mpif.h、runtime、整数边界、Conan component 和 binary identity。
2. 对 BLAS/LAPACK 参与的 LP64 数值库，必须把 provider、Fortran INTEGER 宽度、符号和调用约定写入证据，并以真实消费者和数值结果验证，不能只看链接成功。
3. 对依赖 MPI_Abort 结束且使用 $ORIGIN RUNPATH 的 CTest harness，应从原 runtime directory 执行 ELF、引用可能为空的 list 参数，并在 abort 前 FLUSH 完成标记。
4. 对确实无公共头的 Conan library，应设置 self.cpp_info.includedirs = []，并通过不硬编码 -I/-L/-l 的真实 CMakeDeps imported-target 消费者验证。

## 已完成的证据材料

- 当前待推送候选由本 PR 的 Pre-PR 合同绑定；提交前以合同结果文件回读 exact HEAD/tree。新候选尚未获得远端 Review、Buildbot CI 或独立 W4 结果。
- 上一远端候选 HEAD：0341ea496eedba17766584687da26840d14417b2；其独立 W3 为 100/100 上游 CTest、2/2 BLACS_GRIDEXIT marker、1/1 Conan CMakeDeps 两 rank 消费者，输入 SHA-256 2c51a5d00154b616ae98c6b5bcce9eb857ef6378899905d0ea300efc4360d9e5。
- 上一远端候选 Buildbot：builder 1 / #28982，BUILD 32358；7/7 steps results=0，ci_pr_number=5839，ci_revision 精确绑定 0341ea496eedba17766584687da26840d14417b2。该证据不跨候选复用。
- 新候选的 AI Review、Buildbot CI 和独立 W4 尚待当前 HEAD 完成；在新 HEAD 通过后再回填对应的 exact-head 证据。

## 当前状态与边界

PR #5839 保持 OPEN，源分支为 feat/scalapack-2.2.3，目标分支为 main；上一远端候选的 CI 和 AI Review 已通过，discussion 为 0/0；当前待推送候选的 Review、CI 和 W4 尚待完成。本 Issue 只申请路径 C 候选确认，不宣称已获得路径 C 分值，也不把 MPICH 的 Conan 制品发布、合入或 post-merge release 结果提前写成已完成。合入后仍须按新鲜隔离 Conan home 回读 OHOS/arm64 的 RREV、PID、PREV 和 info_invalid=0。

## 建议验收项

1. 复核 Fortran compiler/runtime、BLAS/LAPACK LP64 与 MPI C/Fortran provider 的同一身份、整数宽度、符号和运行时证据。
2. 复核上游 100/100 CTest、2/2 BLACS marker、1/1 两 rank 消费者、ELF 签名和重定位证据，并确认不存在 C-only 或单 rank 替代。
3. 合入后以新鲜 --build=never 检查正式 OHOS/arm64 发布的 RREV/PID/PREV、组件目标和多 rank 消费闭环。

## 申请边界

| 路径 | 分值 | 说明 |
| --- | --- | --- |
| 路径 A | 基础适配候选 | 完成 Conan 配方、OHOS arm64 构建、签名和上游测试闭环。 |
| 路径 B | 10 分候选 | 提交 E2156/E2155 配对草稿，沉淀 MPI/Fortran、BLACS harness 和 headerless Conan 的可复用规则。 |
| 路径 C | 仅申请候选确认 | 依据依赖链/全量测试成本、项目专用工具链和 Fortran/BLAS/LAPACK/MPI 混合 ABI 申请候选，不直接声明分值。 |
| 其他 | 不单独申报 | 配套知识随软件 PR 提交，不创建独立 Issue/PR。 |

*最终以评审委员会审核结果为准。*

## 需要评审委员会确认的问题

1. 是否认可 ScaLAPACK 2.2.3 作为路径 C 高难度挑战候选。
2. 对 Fortran、BLAS/LAPACK 和 MPI 三条边界，路径 C 的最低验收证据是否还需补充其他项目。
3. 是否认可 100/100 上游 CTest、2/2 BLACS marker 和 1/1 两 rank 消费者作为当前阶段的完整测试证据。
4. 若当前暂不纳入路径 C，是否认可本 PR 先按路径 A + 路径 B 继续评审。
