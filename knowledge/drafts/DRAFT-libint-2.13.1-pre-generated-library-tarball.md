# DRAFT-libint-2.13.1-pre-generated-library-tarball

**问题**：适配 libint 2.13.1 时，使用 GitHub tag 源码包（refs/tags/v2.13.1.tar.gz）无法进入可用的
Conan 干净构建路径——该源码包是"编译器 + 预生成库"双态仓库，默认 CMake 构建需先编译 libint 编译器
（build_libint）再运行 export 生成库源码，串行且极慢，不适合配方构建。init-build 亦将其误判为
autotools，导致 G0 clean-verify 的 `./configure` 直接报 `No such file or directory`（exit 127）。

**根因**：libint 仓库包含 `src/bin/libint`（编译器/生成器）与 `export/`（导出机制）；官方在
GitHub release 中同时发布预生成的 lmax=6 标准库 tarball（`libint-2.13.1.tgz`）。该资产内含完整、
可直接构建的 CMake 库工程（`srclist.cmake` 声明约 7887 个库源文件，含 `tests/unit`、`python/tests`），
是配方应选用的官方源。C++11 API（默认开）依赖 header-only Eigen3；Boost 为可选，缺失时 CMake
在配置期自动解包 `external/boost.tar.gz`。

**方案**：
1. `conandata.yml` 的 `sources.url` 指向官方 release 预生成库 tarball：
   `https://github.com/evaleev/libint/releases/download/v2.13.1/libint-2.13.1.tgz`
   （sha256=029e1347…，与本地下载一致），而非 `refs/tags/v2.13.1.tar.gz`。
2. 配方用 CMake 模板（非 autotools）；`generate()` 关闭可选构建
   `LIBINT2_ENABLE_FORTRAN/MPFR/PYTHON=OFF`，保留 header-only C++ API。
3. `requirements()` 声明 `eigen/3.4.1`（`transitive_headers=True`）；`package_info()` 设
   `cpp_info.libs=["int2"]`。
4. 注意 libint2 2.13 的 API 变化：`Engine` 为非模板类，构造参数为
   `(operator, max_nprim, max_l)`，如 `libint2::Engine engine(libint2::Operator::overlap, 1, 0)`。

**验证**：
- `conan-verify` G0-G4/L2/L4/L5 全绿（G2 conan create 干净构建通过，产物 libint2.a）。
- 上游测试 ctest 13/13 通过（eritest/unit/hf/hf++）。
- `test_package` 消费者测试实跑：构造两个归一化 1s Shell，`Engine<overlap>` 计算重叠积分断言
  S_ss ≈ 1.0（R34 实质调用被测包 API，test() 用 `self.run` 执行二进制）。

**适用边界**：适用于同型"编译器生成库源码"双态架构项目（libint 后续版本、mpqc 系、其它 codegen
型库）；OHOS/Linux 交叉编译均可复用。不适用于无需生成器的纯 CMake 库（直接用官方 tag 源码包）。
需要自定义 AM/orderings 时仍必须走源码包 + build_libint 流程（预生成资产由官方发布固定）。

**反例/限制**：libintl/gettext 类 NLS 库与本候选无关；本库适配中的网络下载超时（E017）、CMake
平台识别（E092）为通用条目，已在既有知识库覆盖，未并入本草稿。
