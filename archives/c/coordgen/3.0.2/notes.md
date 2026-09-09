# coordgen 3.0.2 adaptation notes

- 上游为 Schrödinger 官方 `coordgenlibs`（https://github.com/schrodinger/coordgenlibs），BSD-3-Clause 的 C++11 2D 分子坐标生成库（sketcher minimizer）。v3.0.2 发布 tarball SHA256 已在 `conandata.yml` 核验。CMake `project(coordgen)`；本包包名取任务卡口径 `coordgen`。
- 零补丁。上游 CMake 原样使用：`COORDGEN_BUILD_SHARED_LIBS` 随配方 `shared` 选项（默认 static，仓库惯例）；`COORDGEN_RIGOROUS_BUILD=ON`（上游 CI 口径 -Wall -Wextra -Werror，库本体在 OHOS clang 15 下零告警通过，原生探索实证）。
- 配方以 `cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})` 传入兼容变量：上游 CMakeLists 首行 `cmake_minimum_required(3.2)` 的检查发生在 `project()` 加载 toolchain 之前，写进 CMakeToolchain 的 `tc.variables`/`tc.cache_variables`（toolchain 文件内 `set()`）在该检查点不可见，首轮 conan-verify G2 实证失败；必须是命令行缓存变量（正式知识 E103）。
- 上游 CMakeLists 固定 `set(CMAKE_CXX_STANDARD 11)`，低于 profile `cppstd=17`：按上游显式选择以 11 编译库（conan_toolchain 的 17 被上游覆盖，CMake 有明确告警可查）；package_id 仍按 profile cppstd 生成。下游最低标准为 C++11，已在软件级 manifest 声明。
- 默认 `COORDGEN_USE_MAEPARSER=OFF`（上游默认）：模板数据编译期内嵌（`CoordgenTemplates.cpp` + `templates.mae`），库本体零依赖，`requirements()` 为空。上游测试所需的 maeparser/Boost 只在原生探索阶段使用，不进入包依赖链。
- 上游安装产物：`libcoordgen.so`/`libcoordgen.a`（VERSION 3.0.2 SOVERSION 3）、头文件 20 个（`include/coordgen/`，上游 install(FILES) 恰 20 项）、`lib/cmake/coordgen-config.cmake`（install(EXPORT coordgen-targets)，目标名 `coordgen::coordgen`）。`package_info()` 与之对齐。
- 原生探索（阶段 E，与上游 CI `.azure-pipelines/linux_build.yml` 同构）：Release + `COORDGEN_RIGOROUS_BUILD=ON`，shared 与 static 两变体 configure/build/install，`make -j1`。依赖经 conan 消费侧提供：maeparser/1.3.3（W0 实证 OHOS binary 可取）、boost/1.84.0。
- 上游测试对接（消费侧零上游补丁，经 `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` 注入）：
  - 上游 `if(TARGET maeparser)` 命中 conan CMakeDeps 目标（`cmake_target_name` 覆盖为无命名空间 `maeparser`，先例 MilkyTracker），跳过 `find_or_clone_maeparser()` 网络克隆路径。
  - 仓库 `boost/1.84.0` 包无预编译 `libboost_unit_test_framework`：按 Boost.Test 官方"手动静态编译"模式（`#define BOOST_TEST_SOURCE` + `boost/test/impl/*.ipp`，maeparser 配方同款先例 ut_stub.cpp）在消费侧提供 `Boost::unit_test_framework` 目标；`Boost::filesystem` 由 conan boost 包组件目标直接提供。
  - `libmaeparser.a` 含 boost::iostreams 未定义符号，裸变量 `${maeparser_LIBRARIES}` 链接不携带传递依赖：注入模块中补为 `maeparser Boost::iostreams`（iostreams 组件目标自带 zlib::zlib 依赖）。
  - clang 15 对上游测试代码两处未使用变量报 `-Wunused-but-set-variable`（上游 CI gcc 不触发）：消费侧仅将这一条 `-Werror` 降为 warning，其余 `-Werror` 全保留。两处：`test/coordgenBasicSMILES.h:33`、`test/test_coordgen.cpp:313`。
- 上游测试结果（沙箱 HOME，`ctest --output-on-failure`）：shared 与 static 两变体均 3/3 CTest 通过（example + test_coordgen + test_smilesparser）。Boost.Test 用例级直跑：test_coordgen 16 例、test_smilesparser 4 例，20/20 全过、0 失败、0 跳过；取数命令 `grep -c 'Leaving test case' <log>`。
- 上游缺陷记录（未修改上游测试文件）：`test/CMakeLists.txt` 的 `test_smilesparser` CTest 条目 `COMMAND` 误指向 `test_coordgen` 二进制（`add_test(NAME test_smilesparser COMMAND ${CMAKE_BINARY_DIR}/test/test_coordgen)`），该 CTest 条目重复执行 test_coordgen。真实 `test_smilesparser` 二进制另行直跑，4 例全过。两个二进制在两变体下均通过，缺陷不影响测试覆盖结论。
- `test_package/example.cpp` 只用安装后的公开 API：`sketcherMinimizerMolecule::addNewAtom/addNewBond`、`atom->setAtomicNumber`、`bond->setBondOrder`、`sketcherMinimizer::initialize/runGenerateCoordinates`、`atom->getCoordinates`、`molecule->getAtoms/getBonds`。程序化构建苯环（6 C，Kekulé 交替键序 1/2），校验计数、坐标有限性、键长合理且近正六边形（内置模板识别生效）、原子位置互异：30/30 检查通过。
