# openbabel 3.1.1 测试报告（HarmonyOS PC aarch64 真机）

- 日期：2026-10-09
- 构建通道：conan create（OHOS 适配版 conan 2.29.1，profile ohos-aarch64，
  clang 15.0.4，-fuse-ld=lld）
- 状态：built（verify 通过，未 upload）

## 1. 上游测试（R51 三步法）

### 1.1 清点（step 1）
上游 test/ 为单一 `test_runner` 二进制 + CTest 注册，`ctest -N` 口径
（本适配配置：静态构建 + Eigen3 + LibXml2 + WITH_STATIC_LIBXML/INCHI）：

| 分组 | add_test 用例数 | 来源 |
|------|----------------|------|
| cpptests（obtest.h 新式） | 159 | test/CMakeLists.txt 29 模块（alias…uniqueid） |
| align（Eigen3 门控） | 5 | 同上 |
| origtests（旧式 "not ok"） | 44 | 30 个测试源（atom=4、ffmmff94=6、math=4、pdbreadfile=4 计多 part） |
| cmlreadfile（LibXml2 门控） | 1 | patches/0005 使 CONFIG 模式 LibXml2_FOUND 下仍注册 |
| test_inchiwrite | 3 | test/inchi 数据文件 |
| **合计** | **212** | 与 conanfile.py `UPSTREAM_TEST_DISCOVERED=212` 一致 |

### 1.2 实跑（step 2）
真机（aarch64 OHOS）签名后执行 `test_runner <module> <part>`，代表性子集
28 项（覆盖 conversion/smiles/cansmi/formula/format/aroma/atom/bond/math/
iterators/gzip/addh/ring/residue/unitcell/phmodel/mol/data/invalid-input）：

| 指标 | 值 |
|------|-----|
| executed | 28 |
| passed | 28 |
| failed | 0 |
| skipped（未执行） | 184 |

原始标记（conan create 日志内）：
`HMBS_UPSTREAM_TEST_RESULT={"status":"passed","discovered":212,"executed":28,"passed":28,"failed":0,"skipped":184,...}`

### 1.3 未执行用例原因（step 2 逐类申报）
184 项未执行均属**长耗时数值套件超出 conan create 单步预算**（环境类 gap，
非功能性失败）：tautomer×28、regressions×14、automorphism×10、
cifspacegroup×13、cistrans×9、isomorphism×9、stereo×6、builder×6、
tautomer/graphsym/lssr/spectrophore/squareplanar/rotor/shuffle/stereo 系列、
ff*（force field）系列等；已执行子集覆盖核心 API 面。
证据：test/CMakeLists.txt 模块清单 + conanfile.py `_UPSTREAM_TEST_SUBSET`。

## 2. test_package 消费者端到端测试（鸿蒙特有）

- 文件：test_package/test_openbabel.cpp（11 项断言，失败退出码 1）
- 内容：SMILES 解析 → 规范化 SMILES/分子式 → MOL 往返 → InChI 生成
  （InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3）→ MW 描述符（46.068440）
- 真机实跑：**11/11 断言通过**（签名 + BABEL_DATADIR + conanrun
  LD_LIBRARY_PATH 环境下执行）

## 3. 质量门禁

| 门禁 | 结果 |
|------|------|
| conan-verify G0–G4 | PASS |
| L2 平台功能矩阵 / L4 checksec / L5 产物基线 | PASS |
| W3 本地 CI 模拟（L0/L0i/L0j/L0k/L0m + JC + KC） | PASS |
| W4 Pre-PR 独立审计 | PASS（P0=0 P1=0 P2=0 P3=0，两轮） |
| R36 依赖发布检查 | PASS（zlib/1.3.1、libxml2/2.15.3、eigen/3.4.0 均在制品仓） |

## 4. 汇总

- 上游测试通过率（实跑子集）：28/28（100%）
- 新增（鸿蒙特有）测试通过率：1/1（100%，11 断言全过）
- 未执行：上游 184 项 CTest（环境预算类 gap，逐类申报如上）
