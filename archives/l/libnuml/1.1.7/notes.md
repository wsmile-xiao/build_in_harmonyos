# libnuml 1.1.7 适配 notes（HarmonyOS PC）

## 基本信息

- 名称：libNUML（Numerical Markup Language 读写库，C++）
- 版本：1.1.7（上游 tag v1.1.7）
- 上游仓库：https://github.com/NuML/NuML
- 源码包：https://github.com/NuML/NuML/archive/refs/tags/v1.1.7.tar.gz
- sha256：`820d854355d80a3fe6dbe6c5428c45d42542541213cf0c3b3aee705f8ba1399f`
- License：LGPL-2.1-or-later（libnuml/LICENSE.txt）
- 构建系统：CMake（`libnuml/CMakeLists.txt`，LANGUAGES CXX）
- 产物：共享 `libnuml.so`（SOVERSION 1）＋静态 `libnuml-static.a`；头文件 `include/numl/`

## 上游测试盘点（R51 口径申报）

| 项目 | 结论 | 来源 |
|------|------|------|
| tests/ 或 test/ 目录 | 无 | v1.1.7 tag 内容清单（libnuml/ 下仅 CMakeLists.txt、src/、examples/、docs/、CMakeModules/、submodules/） |
| add_test() 注册 | 无 | 源码检索无 add_test；`enable_testing()` 存在但零注册 |
| ctest 可发现用例 | 0（`ctest -N` 的 `Total Tests: 0` 为准） | 配方 build() 中实际执行 `ctest -N` 并解析 |
| examples/ | 仅为示例（c++/java/python），`WITH_EXAMPLES=OFF` 默认不编 | libnuml/examples/CMakeLists.txt |
| WITH_CHECK | 默认 OFF；无配套测试目标 | libnuml/CMakeLists.txt |

结论：上游无测试套件，配方输出 `status:"no_tests"` 标记，
test_package/MANIFEST.yml 已写入 `upstream_tests_exist: false`＋审计说明。

## 依赖说明（W0）

| 依赖 | 状态 | 处理 |
|------|------|------|
| libSBML（XML 层，硬依赖，`find_package(LIBSBML REQUIRED)`） | 未进制品仓（archives/ 全树无 sbml 记录） | 配方内构建官方 5.21.0（core only，无 L3 包、无绑定），静态私有 |
| expat（libSBML 的 XML 解析后端） | 未进制品仓 | 配方内构建官方 2.7.1，静态私有 |
| zlib/libxml2 | 不需要（`WITH_ZLIB=OFF`，压缩读写不支持，已在 PR 正文说明） | 无 |

单 PR 约束（R36）下采用内嵌私有静态构建，与已合入的
libcombine/0.2.20（内嵌 libSBML 5.20.5）与 libsedml/2.0.33
（内嵌 expat 2.7.1＋libSBML 5.21.0＋libNuML 1.1.7）同口径；
三者源码 URL＋sha256 均引官方 release，libNuML 的 sha 与
libsedml 配方内记录一致。待 libSBML/expat 独立成包后，
本配方应改为 `requires` 引用（届时以 R36 为准）。

## 配方实现（执行顺序）

1. `source()`：解压 libnuml 到 `numl-src/`（包内 `libnuml/` 子目录构建），
   expat/libsbml 解压到 `vendor/{expat,libsbml}/`。
2. 构建前统一处理所有 vendored `FindZLIB.cmake`
  （缺 zlib 时 `check_library_exists` 在 CMake 4.x 下硬失败，
   加 `if(LIBZ_CMAKE_PATH)` 守卫；`WITH_ZLIB=OFF` 下探针结果无用）
   与 `FindEXPAT.cmake`（try-compile 双失败的 `FATAL_ERROR` 降级为
   `WARNING`，XML_STATIC 缺失在非 Windows 目标功能中性），
   并给 `libnuml/CMakeLists.txt` 补 `LANGUAGES C CXX`
  （FindEXPAT 懒加载 `enable_language(C)` 在 OHOS 工具链下 mishandle）。
   以上三处均为构建期文件改写（`replace_in_file`），不进 `patches/`，
   无 `__OHOS__` 平台宏（PF5）。
3. expat：`BUILD_SHARED_LIBS=OFF`，关闭 tests/examples/tools，装入 `deps/`。
4. libSBML：`WITH_EXPAT=ON`，`WITH_LIBXML/WITH_XERCES/WITH_ZLIB/WITH_BZIP2=OFF`，
   关闭 SWIG/示例/测试，静态装入 `deps/`，
   `EXPAT_INCLUDE_DIR/LIBRARY` 显式指向私有 expat。
5. libNuML：`LIBSBML_DIR/EXPAT_DIR/CMAKE_PREFIX_PATH` 指向 `deps/`，
   `WITH_SWIG/WITH_EXAMPLES/WITH_CHECK=OFF`，
   `shared=False` 默认仅静态（`shared=True` 时附带 `libnuml.so`）。
6. 构建后校验：`build-numl` 下 `libnuml-static.a` 必须存在，
   且 `llvm-nm/nm` 探针确认含 `NUMLDocument` 符号。
7. 上游测试证据：`ctest -N` 解析 `Total Tests: N`（唯一数字源），
   N==0 时输出 `HMBS_UPSTREAM_TEST_RESULT`（no_tests），N!=0 直接失败。
8. `package()`：合并 `deps/include`、`deps/lib` 的 `.a`
  （numl-static、sbml-static、expat）与头文件；
   `shared=True` 时附带 `.so*`。
9. `package_info()`：静态链接顺序 `numl-static → sbml-static → expat`
  （`shared=True` 时首项为 `numl`），`system_libs=["m"]`。

全程 `cmake -B/-S/--build/--install`，`CMAKE_POSITION_INDEPENDENT_CODE=ON`，
安装 `lib/` 目录统一（防 ohos.toolchain 下 `lib64` 默认）；
工具链优先使用可发现的 ohos.toolchain.cmake，缺失时生成
fallback（`CMAKE_SYSTEM_NAME=Linux`＋OHOS clang，使 `if(UNIX)` 成立，
产物仍为原生 OHOS/aarch64 二进制）；llvm-ranlib 缺失时用
`llvm-ar s` 垫片；TMPDIR 指向可写目录（只读 /tmp 兼容）。

## test_package 说明

- 直调 cxx 编译（libcombine 0.2.20 同款理由：vanilla CMake 4.x
  无 Platform/HarmonyOS 模块，消费者 CMake configure 会倒在平台模块上）。
- 唯一依赖为被测包自身（vendored 静态库随包发布，无外部 requires，PF4 安全）；
  `-I/-L/-l` 全部取被测包 `cpp_info`，缺失目录只告警不猜测。
- `test_numl.cpp` 7 个 CHECK：建档、ontology terms＝2、result component 及
  dimension 计数、写文件非空（含 size 明细后缀）、读回零错误且计数一致、
  level/version＝1/1、错误日志为空；`main` 返回非零即失败，无空壳（R34）。
- `test()` 单一数字源：逐行匹配 `^CHECK <name>: PASS|FAIL`（允许 ` (detail)`
  后缀），与 `TEST_NUML_DONE passed=/total=` 交叉一致后输出
  `HMBS_TEST_PACKAGE_RESULT`（双通道）；计数矛盾直接失败，不做算术修补。
- 上游证据双通道发射并落盘 `hmbs_upstream.json`，经 `package()` 随包发布到
  `res/`，`test_package` 每轮原样复发（libsedml/2.0.33 同款模式）。

## 验证结果

- 本地未跑 conan（按任务守则，编译验证在真机内执行）。
- 待 HMBS 真机预检回填：上游 `ctest -N` 输出、`test_numl` 输出与两行 JSON 标记；
  PR 正文通过率以预检日志为准，不估算。

## 已知限制

- 压缩相关 SBML/SEDML 读写（需 zlib/bzip2 的 `.gz/.zip/.bz2`）暂不支持，
  因 `WITH_ZLIB/WITH_BZIP2=OFF`；纯 NuML XML 读写不受影响。
- `shared=True` 分支可构建但未经真机验证，默认静态分支为验证目标。
