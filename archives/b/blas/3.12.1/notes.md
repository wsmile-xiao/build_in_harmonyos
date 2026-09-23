# blas 3.12.1 适配笔记（HarmonyOS PC / os=OHOS arch=armv8）

## 软件定位

Netlib 参考 BLAS（Basic Linear Algebra Subprograms）。netlib 官方声明
REFERENCE BLAS 现已并入 LAPACK 发行（netlib.org/blas/ 页面明确："BLAS is now
included in the LAPACK library. See LAPACK website for Download"），独立的
`blas.tgz` 是不含 3.12.1 的历史包。故本包源码取 netlib 官方
`https://www.netlib.org/lapack/lapack-3.12.1.tar.gz`（SHA-256
37b00c90... 实测核验），只构建其中 BLAS/ 组件——与仓库 lapack/3.12.1、
cblas/3.12.1 同源同版本（后两者取 GitHub Reference-LAPACK v3.12.1 tarball，
内容一致、打包不同故 SHA 不同）。

## 构建方案

- 纯 Fortran 77（BLAS/SRC 157 个 .f/.f90 文件）。鸿蒙设备无 gfortran，
  `tool_requires flang-ohos/20.1.0`（LLVM Flang）编译，同 lapack/openblas/
  cblas 先例（E242 LLVMFlang 经验）。
- 走上游 make 路径：`BLAS/Makefile` include 顶层 `make.inc`；配方
  `generate()` 写入 make.inc（字面路径，无环境变量依赖），`build()` 依次
  `make -C BLAS`（libblas.a）、`make -C BLAS/TESTING`（12 个 blat 驱动）、
  `make -C BLAS/TESTING run`（上游测试）。
- 不走 CMake：顶层 CMake 的 BLAS 目标需 Fortran 链接探针，flang-ohos 精简
  运行集无法完成（同 lapack 先例）。
- flang 实测可用的完整参数形态：
  `flang --target=aarch64-linux-ohos --sysroot=<SDK>/sysroot -resource-dir=<SDK llvm>/lib/clang/15.0.4`，
  链接加 `-L<SDK llvm>/lib/aarch64-linux-ohos -lFortranRuntime -lFortranDecimal -lm`；
  flang 运行期需 `LD_LIBRARY_PATH` 指向 SDK llvm/lib 与 flang 包 lib。

## 依赖与链接形态

- 构建期依赖：`flang-ohos/20.1.0`（tool_requires）。无运行期第三方依赖
  （参考 BLAS 是自足的纯 Fortran 计算库）。
- libblas.a 内 `xerbla.o` 引用 `_FortranAio*`/`_FortranAStopStatement` 等
  Fortran IO 符号，消费方链接需带上 Fortran 运行时；`package()` 随包复制
  `libFortranRuntime.a`/`libFortranDecimal.a`（同 lapack 先例），
  `package_info` 的 `libs` 列出 blas + 两个运行时。
- 参考 BLAS 无头文件；消费方以 C 直接调用 Fortran LP64 符号
  （`ddot_`/`dgemm_` 等尾下划线约定）。

## 上游测试与补丁

- 套件：`BLAS/TESTING`，12 个 blat 驱动 = level1/2/3 × s/d/c/z 四精度。
- 运行方式：`make run`（blat1 自包含；blat2/3 读源码树 `*blat2.in`/`*blat3.in`
  数据文件）。统计单位 = 测试驱动验证行（blat1 的 `----- PASS -----` 与
  blat2/3 的 `PASSED THE ... TESTS` 行），取数 conanfile.py `build()` 内
  `*blat*.out` 正则计数。
- **补丁根因（E-新增知识候选）**：上游 3.12.1 的复数 blat1 测试驱动
  `cblat1.f`/`zblat1.f` 的 TRAT 比较链缺失实数版（`sblat1.f`/`dblat1.f`）
  已有的 `ELSE IF (SNRM == ZNRM) THEN TRAT = ZERO` 短路分支（差异经
  diff 逐行确认：实数版第 1254/1302 行有、复数版对应位置无）。当测试值
  `VALUES(9) = SXVALS(V0,2) = HUGE**2 = +Inf`（overflow）输入时，库正确
  返回 Inf，期望值 ZNRM 亦为 Inf，但复数版走到
  `TRAT = (ABS(Inf-Inf)/Inf)/(2N·ULP) = NaN`，`TRAT.NE.TRAT` 恒真 → 误报
  FAIL（16 个）。实测诊断：最小复现确认 `SCNRM2((huge,-3*huge)) = Inf` 是
  正确 IEEE 行为（sqrt(huge²+9huge²) 溢出为 Inf），故障在测试驱动比较链。
  补丁为两个后缀 `patches/` 文件，补齐该分支，与实数版对齐；应用后
  TOTAL=246 PASS / 0 FAIL（32 个误报清零）。
- 结果：TOTAL = 246 PASS + 0 FAIL（stest1..ztest3 依次
  13/32/14/13/32/14/10/34/20/10/34/20）。

## 已核对的上游行为

- blat1 驱动含 Algorithm 978（Anderson 2017）安全缩放参考计算，覆盖
  0/极小/小/ulp/1/1·ulp/大/极大/Inf/NaN 十档测试值——Inf/NaN 用例正是
  补丁所涉场景。
- blat2/3 的 error-exits 与 computational tests 均通过，`END OF TESTS`
  标记齐全。
- 测试驱动退出码为 0 不反映单用例 FAIL（FAIL 通过输出文本标记），故
  conanfile 以正则统计 PASS/FAIL 行作为门禁，失败任一即 raise。

## 消费者验证（test_package）

- C 程序 `test.c` 直接链接 libblas + Fortran 运行时，调用 `ddot_`/`dasum_`/
  `daxpy_`/`dgemm_`（level 1/2/3，Fortran 列主序 ABI），4 项手算断言全过
  （ddot=32、dasum=6、daxpy→{6,9,12}、dgemm C={19,43,22,50}）。真实数值计算
  验证，非符号解析。
---

**编译结束**: 2026-09-15 21:25
**最终状态**: published

## 知识候选台账（knowledge_candidate_ledger）

候选 1：netlib BLAS 复数 blat1 测试驱动缺 `SNRM==ZNRM` 短路分支致 Inf 用例误报 FAIL
- 真实错误：conan create 上游测试 cblat1/zblat1 各 16 例 `test=NaN`（`SCNRM2`/`DZNRM2`，IV=9 Inf 输入）
- 根因：上游 3.12.1 cblat1.f/zblat1.f 的 TRAT 比较链缺失实数版（sblat1.f/dblat1.f）已有的 `ELSE IF (SNRM == ZNRM) THEN TRAT = ZERO` 短路分支；库对 Inf 输入返回 Inf 是正确 IEEE 行为（sqrt(huge²+9huge²) 溢出），复数版走到 `TRAT=(ABS(Inf-Inf)/Inf)=NaN`，`TRAT.NE.TRAT` 恒真 → 误报
- 修复：patches/0001-0002 补齐该分支（与实数版 diff 逐行对齐），修复后 TOTAL=246 PASS / 0 FAIL
- 验证：conan create 复跑 0 FAIL；最小复现 SCNRM2(1,(huge,-3*huge))=Inf 实证库行为正确；W3 本地 CI 通过
- 适用范围：flang/gfortran 编译 netlib 参考 BLAS/LAPACK 运行复数 blat1 驱动的场景；任何复用 Algorithm 978 测试值（含 Inf/NaN）的驱动
- 四范围查重：index.tsv（E109 缺 gfortran / E242 Fortran module ABI / E306 std::polar NaN / E535 cgns ctest 均不覆盖）+ doc/ + graph/ + drafts/（无 blas/blat/nrm2 草稿）→ 未命中
- 七轴查重：exact_duplicate=否；causal_duplicate=否；trigger_overlap=否（触发面为 flang 复数 nrm2 测试，既有条目均无）；solution_overlap=否（既有条目无 TRAT 短路比较模式）；combination_novelty=有（测试驱动比较链与 IEEE Inf 语义组合）；boundary_novelty=有（Inf/NaN 档测试值处理边界）；test_migration_novelty=有（复数/实数驱动不对称的补丁迁移模式）
- 关系：similar_to=E306（同为 NaN 污染比较，但 E306 是 C++ std::polar 输入契约、本候选是 Fortran 测试驱动比较链）；caused_by=上游驱动不对称；prerequisite_of=无；conflicts_with=无
- 适用边界/反例：仅 Inf 输入下 SNRM==ZNRM（含两者均 Inf）比较；NaN 走既有分支不受影响；若上游新版本已修复则无需补丁
- **路径决定：new_draft（路径 B）**——已建 knowledge/drafts/DRAFT-blas-3.12.1-blat1-inf-shortcircuit.kv/.md 配对草稿，随本库 PR 一并提交
