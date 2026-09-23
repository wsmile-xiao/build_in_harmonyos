- **三方库名称**：libint2
- **上游版本**：2.7.2
- **上游仓库地址**：https://github.com/evaleev/libint
- **适配路径**：路径 B（贡献创新 / 知识库扩展）
- **使用知识库**：E480（header-only 依赖用 `transitive_headers=True` 消费）、E216（CMakeDeps 不传播依赖 include → 消费者编译失败）、E092（CMake 不识别 HarmonyOS host 平台）、E247（上游 `.pc` 元数据不完整，同类）、`DRAFT-boost184-component-pack-static-libcxx-testbin`（OHOS `libc++_shared.so` 加载失败 → `-static-libstdc++`，本次复用不重复入库）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| CTest 用例 | 12 | 来源：上游 `CMakeLists.txt` 注册（4 个 build fixture + 8 个 run）：`libint2/eritest/{build,run0..run4}`、`libint2/unit/{build,run}`、`libint2/hf/{build,run}`、`libint2/hf++/{build,run}` |
| 单元测试（入口内部） | 17 | 来源：`tests/unit/test.cc`（Catch2），共 **2,104,689** 条断言，覆盖 1-body/2-body/基组/C API/壳层序/精度等 |
| 集成测试 | 2 | 来源：`tests/hartree-fock/hartree-fock{++,}.cc`，HF 能量与参考值 `-74.942080057696` 对比（tol 1e-11） |
| **合计** | **12（CTest 唯一入口）** | 断言总量 2,104,689（unit）+ 5 个 eritest 内核对比 + 2 个 HF 流水线校验 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| CTest 用例 | 12 | 不变 | 12/12 全部通过（在 OHOS 原生环境真实执行，非 NOT_RUN） |
| 鸿蒙/消费者特有价值入口 | 4 | 新增 | 详见下方"补全测试用例说明" |
| **合计** | **16** | **+4** | 上游 12 + 新增消费者入口 4（唯一入口计数，不按内部断言重复计） |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] 是，存在对上游测试用例的修改

> 上游测试源码（`tests/eri/test.cc`、`tests/unit/*`、`tests/hartree-fock/*`）与上游 CMake 测试注册均未改动；
> `patches/` 为空。构建期唯一的链接期配置是 `CMAKE_EXE_LINKER_FLAGS=-static-libstdc++`
> （OHOS 运行期找不到 `libc++_shared.so` 的必需处理，见"补充说明"），它不影响任何测试用例的输入、期望值或数量。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] 否，上游已有测试用例覆盖
- [x] **是**，上游测试入口未覆盖的消费契约，适配后补全了 4 个独立消费者入口

> - **补全原因**：上游 CTest 覆盖的是"库自身的数值正确性"，但没有覆盖**打包后的消费契约**
>   （C ABI、安装包内的基组数据、pkg-config 元数据）。本归档在 `test_package/` 补全这 4 个入口，
>   由 `conan create` 的 test 阶段真实执行。
> - **新增测试文件清单**：
>   1. `test_package/test_package.cpp` — C++ API 消费者：`BasisSet` + `Engine` 计算 H2O/STO-3G
>      重叠矩阵与库仑积分，校验归一化、对称性、置换对称性、同中心 s×p 宇称零元、Schwarz 不等式（9 断言）
>   2. `test_package/test_c_api.c` — C ABI 消费者：`libint2_build_*` 内核分发表注册情况、
>      `libint2_need_memory_eri` 单位与单调性、调用方自备 buffer 的 `init/cleanup` 契约（17 断言）
>   3. `test_package/test_basis.cpp` — 基组数据库完整性：`sto-3g` / `6-31g*` / `cc-pvdz` /
>      `aug-cc-pvdz` 按名加载的基函数数与最大角动量；负向：未知名默认空基组、strict 模式抛异常且
>      错误信息包含真实数据目录（11 断言，证明 `DATADIR` 生效）
>   4. `test_package/test_pkgconfig.c` — pkg-config 消费契约：用安装出来的 `libint2.pc` 的
>      `--cflags/--libs` 真实编译并运行（对上游 `.pc` 渲染缺陷修复的回归守卫）
> - **新增断言总数**：38（9 + 17 + 11 + 1），全部通过。

## 验证结果

- 编译状态：**通过**（`conan create` 干净构建；`conan-verify` G0-G4 全 PASS；本地 W3 CI 模拟 JC/KC/L0/L1 全 pass）
- 上游测试用例通过率：**12/12（100%）**，含 unit 入口 17 case / 2,104,689 断言、HF 能量校验
- 新增测试用例通过率：**4/4（100%）**，断言 38/38

## 补充说明

### 知识库扩展内容（本次 PR 的知识贡献）

**新增草稿（KV/MD 配套，`draft:true` 随 PR 提交，不改动正式 `index.tsv`，由知识库主编审核）**：

| 草稿 | 可复用问题面 | 预审建议 |
|------|-------------|----------|
| `DRAFT-libint2-2.7.2-upstream-pc-template-unrendered-by-cmake` | 上游 `.pc` 模板沿用 autotools `@var@`，经 CMake `configure_file(@ONLY)` 渲染后前缀/版本为空，`pkg-config` 消费者静默拿到垃圾标志 | create（新知，最高相似度 0.22） |
| `DRAFT-libint2-2.7.2-cpp-info-libs-must-use-upstream-output-name` | 上游用 `ARCHIVE_OUTPUT_NAME`/`OUTPUT_NAME` 改过产物名时，`cpp_info.libs` 必须写产物名而非包名 | review-similar（灰区 0.30 → E511） |
| `DRAFT-libint2-2.7.2-compile-time-datadir-macro-for-runtime-data` | 运行期数据目录靠编译期宏（`DATADIR`/`SRCDATADIR`）+ 环境变量定位，Conan 包须在 `package_info()` 补 define | create（新知） |

**复用既有条目**：E480、E216、E092、E247、`DRAFT-boost184-component-pack-static-libcxx-testbin`。

**去重记录**：适配中先写过一条 `DRAFT-libint2-2.7.2-static-libcxx-for-test-binaries`（问题①的 libc++ 教训），
经检索发现仓库已有同因同方案草稿 `DRAFT-boost184-component-pack-static-libcxx-testbin`，故**删除重复草稿**，
改为引用既有草稿，避免重复入库。

### 适配要点（配方层，零源码补丁）

1. **libc++ 运行时**：OHOS clang 默认把可执行文件动态链到 `libc++_shared.so`（只在 SDK sysroot），
   上游 ctest 的 8 个 run 用例会以 `Error loading shared library libc++_shared.so` 全挂；
   配方对 exe 追加 `-static-libstdc++`（静态库产物不受影响），修复后 12/12 通过。
2. **header-only 依赖传递**：libint2 公开头文件需要 Eigen，`eigen/3.4.0` 声明
   `transitive_headers=True`，否则消费者侧 CMakeDeps 不生成 `Eigen3` config。
3. **`.pc` 修复**：`package()` 中用可重定位的 `${pcfiledir}/../..` 重写安装出来的
   `libint2.pc`（上游模板渲染缺陷导致空前缀），并由入口 4 做回归守卫。
4. **打包语义**：`cpp_info.libs = ["int2"]`（上游 `ARCHIVE_OUTPUT_NAME` 产物名）、
   `DATADIR` define（基组数据按名加载）、静态库（R26）。

### 环境与规模

- 环境：HarmonyOS PC / aarch64，clang 15.0.4，Conan 2.29.1，profile `ci/conan/profiles/ohos-aarch64`
- 源码：上游官方 Release 资产 `libint-2.7.2.tgz`（sha256 `a7306f1998a4c0a0babc13d480c62de2631674918e3562c78fb602c77efe0b94`）
- 规模：6520 个 kernel 源文件；本地 W3 完整 CI 模拟约 29.5 分钟（1763s），在 CI 默认 3600s 预算内

### 已知限制

1. Fortran 绑定未启用（`ENABLE_FORTRAN=OFF`，环境无 Fortran 2003 编译器）。
2. `LIBINT2_ENABLE_MPFR`（高精度测试）默认关闭（需 MPFR/GMP C++ 接口）。
3. 使用上游预生成库 tarball 口径；如需自定义积分类型/角动量，须走 libint 编译器路线（本 PR 不涉及）。
4. 未申报高难度挑战：本库为单依赖（header-only）、零补丁、纯静态数学库，不具备高难度举证范式所需的
   运行时/多目标动态语义，如实按路径 B 申报。

### 构建证据与环境说明（conandata 与 W3 证据的关系）

`ci/conan/build_and_test.sh` 在构建前会把 `conandata.yml` 的 `sources.url` 临时改写为
「镜像 + 官方」列表（预下载优化），该改写**没有还原路径**（只有紧随其后的 `file://`
预下载改写带 `trap EXIT` 还原，且它备份的是"已注入镜像"那一版）。因此 W3 本地 CI 实测
（与 CI 实际构建）时 `conandata.yml` 处于注入形态，而**提交内容按 R39/PF7（源 URL 必为
官方源）只保留官方单源**。

两者差异**仅 `sources.url` 一行**：上游源码 sha256 固定值（`a7306f19…efe0b94`）、
`conanfile.py`、`test_package/**` 完全一致；CI 构建期会按同一注入规则再次改写，故 W3 证据
对 CI 可复现。对应 recipe revision：W3 实测 `libint2/2.7.2#b2e10dacf339…`（注入形态），
提交态 `libint2/2.7.2#19f04f48d434…`（官方单源）；`submit` 的 W3 门禁只校验
`exit_code=0` 与 `integrity_hash`（已按同算法独立复算一致），不比较 recipe revision，故不受影响。

### 复现

```bash
conan create archives/l/libint2/2.7.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build="libint2/*"
```
