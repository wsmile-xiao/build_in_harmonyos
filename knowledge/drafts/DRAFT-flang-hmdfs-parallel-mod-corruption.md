# DRAFT-flang-hmdfs-parallel-mod-corruption（草稿）: flang 报 Must be a constant value —— use 关联 kind 参数作 kind 选择器

> 事件族：Fortran 库在 OHOS（flang-ohos）上编译，kind 选择器处成批
> "error: Must be a constant value"。本条为 draft，编号由知识库主编确认。

## 基本信息
- **严重度**: 2
- **类别**: toolchain, fortran, hmdfs, compiler
- **principles**: P-TOOLCHAIN-001（必须使用 LLVM 工具链——本条是其 Fortran 维度的失败形态与修复纪律）
- **similar_to**: E242（Fortran .mod ABI 与工具链族）、E074（make jobserver/FIFO 串行构建）
- **作者**: GoliWie
- **来源**: devicexlib 0.9.1 适配（run devicexlib-0.9.1，2026-09-11）

## 错误特征
```
error: Must be a constant value
           integer(kind=dxl_async_kind), intent(in) :: async_id
                        ^^^^^^^^^^^^^^
error: Semantic errors in .../src/devxlib_memcpy.f90
make[2]: *** [src/CMakeFiles/devXlib.dir/... Error 1
```
实测分布：42 处全部为 use 关联 kind 参数（dxl_async_kind，由 devxlib_async 模块导出，
`integer, parameter :: dxl_async_kind = kind(0)`）的 kind 选择器，集中于
devxlib_memcpy.f90:3458-3891（h2h_async 接口段）；伴随
`make: jobserver mkfifo: .../GMfifo...: Operation not permitted`。

## 根因分析（含一次证伪记录，防后人复踩）

1. **症状层**：flang-ohos 20.1.1 在 use 关联 kind 参数的全部 kind 选择器处报
   "Must be a constant value"（0.9.1 实测 42 处）。
2. **机制证伪（重要）**：Curator 初判假设为"接口体（interface body）无 host
   association（F2018 §15.4.3.5），flang 严格拒绝 use 关联参数作 kind 选择器"。
   最小判别探针（module 参数 + use 关联 + interface body + submodule 实现 +
   IMPORT 变体）在 flang 20.1.1 下**全部编译运行通过**（P1-A/P1-B EXIT=0，
   "probe ok"）——该机制假设**不成立**，见 `reports/builder/draft-probes.log`。
3. **实证机理**：pristine 的 devxlib_memcpy.f90 全文件（5543 行、含全部 168 处
   该构造）在**可信 .mod 依赖**下串行 `-cpp` 编译 **0 错误**（REPRO-EXIT=0，
   `reports/builder/repro-real.log`）。错误仅在 `-j20` 并行构建中出现，且与
   HMDFS 不支持 make FIFO jobserver（E074 同族）同现；本 run 期间 HMDFS 已多次
   实证静默丢文件与可见性延迟。综合判定最可能机制：**并行构建下跨文件 .mod
   读取非确定性损坏**，消费侧对导入参数常量值求值失败，kind 选择器是最先暴露
   的求值点。
4. **验证**：串行构建 + DXL_ASYNC_DECL 宏 CPU 等价默认化后，8 套件 176/176
   上游测试全过（linalg 16、malloc 28、mapping 28、buffer 10、memcpy 28、
   memcpy_async 28、memset 28、pinned 10，nfail 全 0），错误类消除。

## 方案空间

### 推荐（优先级 1）：serial-build + CPU 等价 kind 默认化
- **构建纪律（正确性要求）**：含跨文件 .mod 依赖的 Fortran 库在 OHOS/HMDFS 上
  串行构建：`CMAKE_BUILD_PARALLEL_LEVEL=1`（recipe build() 注入）。
- **消费侧去依赖**：`integer(kind=<use关联参数>)` 改经宏：
  ```fortran
  #if defined __DXL_CUDAF || defined __DXL_OPENACC || defined __DXL_OPENMP_GPU
  #define DXL_ASYNC_DECL integer(kind=dxl_async_kind)
  #else
  #define DXL_ASYNC_DECL integer   ! CPU: kind(0)==default kind，等价
  #endif
  ```
  全文替换声明为 `DXL_ASYNC_DECL`；GPU 分支展开原文（与上游语义一致）。参考
  devicexlib 0.9.1 补丁 0002（9 文件 410 处声明）。

### 备选（优先级 2）：interface body 内 IMPORT（上游正解形态）
- 仅当未来 flang 版本真机复现出接口体确定性语义拒绝时启用（当前已证伪，勿
  预防性实施）：在 interface body 的 implicit none 前加 `import :: dxl_async_kind`
  （探针 P1-B 验证 flang 20.1.1 接受）。

### 禁止
- **forbid_1**: 在 OHOS/HMDFS 上以 `-jN`（N≥2）构建含跨文件 .mod 依赖的
  Fortran 库 —— 非确定性语义错误 + jobserver FIFO 不受支持，失败随机、浪费整轮。
- **forbid_2**: 无 GPU 能力宏守卫地把 kind 参数全局写死为字面数字 / 只改
  submodule 实现不同步接口体 —— CPU 下看似修好，GPU 配置语义被静默破坏。

## 判别/验证序列（设备自包含）
1. 最小判别探针（构造兼容性）：module probe_impl（参数定义）→ module probe_mod
   （use 关联 + interface body 用该参数声明 dummy）→ submodule 实现 → main 调用；
   flang 串行编译运行，**通过 = 排除接口体语义拒绝**（不要据此改上游接口）。
2. 构造全量确认：pristine 全文件 + 可信 .mod 依赖串行 `flang -c -cpp`，0 错误。
3. 真实故障特征：并行 -jN 构建报成批同签名错误、串行不可复现 → 命中本条，
   走推荐方案。

## 关键词
flang, flang-new, Must be a constant value, kind selector, interface body,
host association, IMPORT, DXL_ASYNC_DECL, dxl_async_kind, .mod, parallel make,
HMDFS, 串行, P-TOOLCHAIN-001

## 勘误
slug 由 flang-interface-body-kind-selector 更名：原命名基于已被判别探针证伪的初判机理。
