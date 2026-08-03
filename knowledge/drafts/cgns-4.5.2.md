# cgns 4.5.2 适配知识（路径 B 候选：上游 CTest 测试迁移验证）

## 构建信息
- 构建系统: CMake
- 编译器: clang 15.0.4 (aarch64-linux-ohos)
- 编译选项: 禁用 HDF5 (-DCGNS_ENABLE_HDF5=OFF)，Fortran 未启用，**启用上游测试 (-DCGNS_ENABLE_TESTS=ON)**
- 构建类型: Release

## 问题类别
- 类别: **测试迁移 / 上游 CTest 在 OHOS 平台启用与执行**
- 子类别: CMake 库的上游测试（CTest 注册）在 OHOS 交叉编译环境的启用与真实通过率核验
- 关联: HDF5 可选依赖缺失、Fortran 编译器缺失（平台能力缺口）

## 为什么普通路径 A 不足
1. 路径 A（基础适配）只需"编译通过 + test_package 消费者测试"，常以"上游测试需 HDF5/MPI，不可用"为由直接写 0/N，**未实际启用上游 CTest 核验真实通过率**
2. 本库实测证明：上游 C 测试（24 个 CTest 入口）**不依赖 HDF5 即可完整构建并 23/23 通过**，与"HDF5 缺失导致测试不可执行"的常见假设相反 — 说明按路径 A 惯例写 0/24 是**不准确的**
3. 缺少可复用方法：如何在 conanfile.py 中正式启用 `CGNS_ENABLE_TESTS=ON + cmake.test()`，如何用 `ctest -N` 核验真实注册数、识别上游 SKIP 机制（SKIP_RETURN_CODE 125）
4. 因此需要路径 B：把"上游 CTest 在 OHOS 启用 + 真实通过率核验"沉淀为可复用知识，供其他 CMake+CTest 库复用（解决一类问题）

## 关键适配点
1. CMake 构建系统，无 configure 脚本（注意: 非 autotools）
2. HDF5 可选依赖，当前版本禁用 HDF5 可正常编译（**上游 C 测试不依赖 HDF5 即可执行**）
3. CMake 可能报 "System is unknown to cmake" 的警告，不影响编译
4. OHOS SDK 无 Fortran 编译器（flang/gfortran 均不可用），Fortran 相关构建/测试无法启用
5. **上游 CTest 测试不依赖 HDF5 链接即可完整构建执行** — 与"HDF5 缺失导致测试不可执行"的常见假设相反

## 可复用方法
1. **conanfile.py 启用上游测试**：
   ```python
   def generate(self):
       tc = CMakeToolchain(self)
       tc.variables["CGNS_ENABLE_HDF5"] = False
       tc.variables["CGNS_ENABLE_TESTS"] = True   # 启用上游 CTest
       tc.generate()
   def build(self):
       cmake.configure(); cmake.build()
       cmake.test()   # conan create 时真实执行上游 CTest
   ```
2. **CTest 真实数量与结果核验**：
   - `ctest -N` 获取准确注册数（不要凭 README 印象写数量）
   - `ctest --output-on-failure` 获取真实执行结果
   - 识别上游 SKIP 机制（SKIP_RETURN_CODE 125 → CTest "Skipped"），通过数 = 注册数 - skip 数
3. **依赖缺失时仍可执行的判断**：先查 C 测试链接依赖（`TESTS_LK_LIBS`），HDF5=OFF 时 C 测试仅链 cgns + m，可完整执行

## 验证命令
```bash
# 上游源码临时验证（仓库外探针构建）
cmake -S . -B build \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
  -DCGNS_ENABLE_HDF5=OFF -DCGNS_ENABLE_FORTRAN=OFF -DCGNS_ENABLE_TESTS=ON
cmake --build build -j2 && cd build && ctest -N && ctest --output-on-failure

# 正式配方验证（conan create 内执行）
conan create archives/c/cgns/4.5.2 --version=4.5.2 --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 真实结果
### C 测试（src/tests，CTest 注册）
- 注册数: **24 个**
- 执行: **23 个执行并通过，1 个 test_back_comp skip**（上游 SKIP_RETURN_CODE 125 机制），0 个失败
- **执行通过率: 23/23（100%），另有 1 个 skip**（不写 24/24 通过）
- 证据: `ctest --output-on-failure` → `100% tests passed, 0 tests failed out of 24`，退出码 0；conan create 日志（build() 内 cmake.test()）确认主包阶段执行 24 项

### Fortran 测试（src/tests，CTest 注册）
- 注册数: **10 个**（cgiof_f03/cgwrite_f03/cgread_f03/cgzconn_f03/cgsubreg_f03/test_general_rindf/test_family_treef/test_bboxf/test_complexf/test_particlef）
- 执行结果: **0/10 N/A** — 缺少 Fortran 编译器（flang/gfortran 均不可用），CMake 配置阶段 "The Fortran compiler identification is unknown" 失败

### UserGuide 示例（Test_UserGuideCode，非 CTest 自动化测试）
- C_code: **38 个源文件构建成功**（19 read_* + 19 write_*），明确为非 CTest 自动化测试（不注册于 ctest -N）
- Fortran_code: **36 个源文件，0/36 N/A** — 缺少 Fortran 编译器
- C_code_parallel: **8 个 C 源文件**（read/write_grid_str_parinzone、read/write_grid_str_paroverzone、read/write_flowcentrind_str_parinzone、read/write_flowcentrind_str_paroverzone），需 MPI；本环境无 MPI，未执行；非 CTest 自动化测试

## 新增测试（test_package）
- 消费者测试: 1 个（6 个 CGNS API 断言）→ **6/6 通过（100%）**
- 断言链: cg_open(CG_MODE_WRITE) → cg_base_write → cg_close → cg_open(CG_MODE_READ) → cg_nbases → cg_close

## 适用边界
- 适用于: CMake 构建、上游有 CTest 注册测试、测试不依赖平台缺失能力（HDF5/MPI/Fortran 等）的库
- 不适用于: 上游测试强依赖 HDF5 链接的库（此类需先提供 HDF5）；Fortran 测试（需编译器）
- 测试框架: CTest（上游 `src/tests/CMakeLists.txt` 注册 `add_test`，`SKIP_TESTS` 列表 + `SKIP_RETURN_CODE 125`）

## 已有知识命中和未覆盖结论
- **命中**: `docs/TEST_QUALITY_SPEC.md`（§"构建后立即运行上游测试"、`cmake.test()` 用法、MANIFEST.yml 声明）；`knowledge/operations/build-systems.md` §9（"必须执行官方测试套件"，CMake 用 ctest）
- **未覆盖**: 无 E 条目专门覆盖"上游 CTest 在 OHOS 上启用（CGNS_ENABLE_TESTS=ON）+ 真实通过率核验 + HDF5 缺失不阻塞 C 测试"的具体模式 — 本次为新增可复用知识
- 说明: E213/E214（知识图谱校验 errors）与 E022/E023（POSIX 兼容）均为**公共框架预存问题**，与 cgns 测试迁移无关，不作为 cgns 贡献

## 验证结论
- conan create（ohpcd/stable，启用 CGNS_ENABLE_TESTS=ON + cmake.test()）: 退出码 0，主包阶段执行上游 CTest 24 项（23 通过 + 1 skip）
- conan-verify: G0-G4 + L2/L4/L5 全部 PASS，退出码 0
- W3 本地 CI: setup.sh + build_and_test.sh 通过，退出码 0
- .ci-result.json: 有效（exit_code=0, step=W3_local_ci）
- test_package: 6/6 断言通过
- finish 退出码非 0 来自已获官方确认的公共框架问题（E213/E214 知识图谱 errors + ARCHIVE-SPEC v3.0 废弃的 packaging/.staging-verified 检查），与 cgns 4.5.2 无关
