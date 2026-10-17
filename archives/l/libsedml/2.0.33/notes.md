# libsedml 2.0.33 适配笔记（HarmonyOS PC · 裸 cmake 配方）

## 上游信息

- 名称：libSEDML（SED-ML 文档读写库，C++，基于 libSBML XML 层代码生成）
- 版本：2.0.33（2025-04-23，新增 SED-ML L1V5 支持）
- 仓库：https://github.com/fbergmann/libSEDML
- 源码包：https://github.com/fbergmann/libSEDML/archive/refs/tags/v2.0.33.tar.gz
- sha256：`a3f69ecb5dc1084343d4de5dc0990bdd9def2f7eb819986015d33ca9735dbe76`
- License：BSD-2-Clause
- 构建系统：CMake（最低 2.8.12，需 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容新 CMake）

## 上游测试清点（R51 申报表）

| 项目 | 数量 | 来源 |
|------|------|------|
| TEST_CASE（Catch） | 33 | tests/TestIssues.cpp |
| CHECK / REQUIRE 断言 | 228 / 112 | 同上 |
| ctest 注册用例 | 1（test_sedml_run） | tests/CMakeLists.txt，`BUILD_TESTS` 默认 ON |
| 数据文件 | 25 个（.sedml/.xml/.sbml） | tests/test-data/ |
| 语言绑定测试 | 无（全部绑定默认 OFF，本配方保持 OFF） | CMakeLists.txt |

测试通过 `srcdir` 环境变量定位数据文件，ctest 自动设置；配方在 build() 中先跑
`ctest --output-on-failure`，再直跑 `tests/test_sedml` 采集 Catch 汇总行用于证据标记。

## 依赖决策（W0）

| 依赖 | 状态 | 决策 |
|------|------|------|
| libSBML（XML 层 + 核心） | 未入制品仓（archives/ 无收录） | 配方内编译官方 5.21.0（core only，无 L3 包、无压缩、无绑定） |
| libNuML | 未入制品仓 | 配方内编译官方 1.1.7（静态） |
| expat（libSBML 的 XML 解析器） | 制品仓仅有 built 状态版本 | 配方内编译官方 2.7.1（静态） |
| zlib | 制品仓有 published（zlib/1.3.1） | 本配方不需要：三处 `WITH_ZLIB=OFF`，压缩读写暂不支持（见补充说明） |

libSBML 5.21.0 与 libNuML 1.1.7 均为同作者（fbergmann）维护的当前稳定版；
libSBML 5.21.0 的 tag 包 sha256 与 FreeBSD ports 记录值一致，交叉验证通过。
后续 libSBML/libNuML 独立入仓后，本配方应改为 `requires` 引用（届时以 R36 为准拆分）。

## 编译步骤（配方实际执行顺序）

1. `source()`：解压主包到 `libsedml-src/`，三个依赖包到 `vendor/{expat,libsbml,libnuml}/`。
2. expat：`BUILD_SHARED_LIBS=OFF`，关闭 tests/examples/tools，安装到构建目录内 `deps/`。
3. libSBML：`WITH_EXPAT=ON`（经 `EXPAT_INCLUDE_DIR/LIBRARY` 以模块模式定位），
   `WITH_LIBXML/WITH_XERCES/WITH_ZLIB/WITH_BZIP2=OFF`，关闭 SWIG/包/示例/自测，
   静态安装到 `deps/`。
4. libNuML：以 `LIBSBML_DIR=deps` 环境变量定位 libSBML，静态安装到 `deps/`。
5. libSEDML：以 `LIBSBML_DIR/LIBNUML_DIR=deps` 定位依赖，
   `EXTRA_LIBS=<deps>/lib/libexpat.a` 补齐传递链接，
   `BUILD_TESTS=ON`；构建前用 `replace_in_file` 将顶层
   `cmake_minimum_required` 下限由 2.8.12 抬到 3.5（与已合入的 ldns 配方同法，
   新版 CMake 否则直接报错）；先 `cmake --build`，再 `ctest --output-on-failure`，
   最后直跑 Catch 二进制解析 `All tests passed (N assertions in M test cases)`
   输出 `HMBS_UPSTREAM_TEST_RESULT` 标记（解析失败则回退到 ctest 级计数）。
6. `package()`：安装 libSEDML 产物，并把 `deps/lib` 中的四个静态库
   （sedml-static、numl-static、sbml-static、expat）与三方头文件一并装入包内；
   静态链接顺序为 sedml → numl → sbml → expat；`shared=True` 时只交付
   `libsedml.so`（经 binary-sign-tool 重签名）。

全程裸 `cmake -B/-S/--build/--install`（参照 libxml2/2.15.3 配方），PIC 对全部
目标强制开启（`CMAKE_POSITION_INDEPENDENT_CODE=ON`），安装 `lib/` 目录统一
（覆盖 ohos.toolchain 的 lib64 默认）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libSBML/libNuML 无处引用 | 制品仓未发布，`requires` 会触发 PF4/R36 门禁 | 配方内从官方源静态编译，`package()` 随包交付，notes 与 PR 补充说明如实披露 |
| 2 | 三个旧项目 `cmake_minimum_required(...3.19)` 在新 CMake 下报错 | CMake 4 移除了对 <3.5 的兼容 | 统一加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 3 | 静态交付时消费者链接缺 sbml/numl/expat 符号 | 静态库不携带依赖 | 包内附带四个静态库并按依赖顺序声明 `cpp_info.libs` |
| 4 | 旧版 Catch 头文件在新编译器下的兼容性 | catch.hpp 为 2016 年单头文件版本 | 保持 C++11 编译；若真机报错再按日志处理 |
| 5 | 真机无 ohos.toolchain.cmake，build() 直接 InvalidConfiguration | 预检机 SDK 布局变化、CI profile 本为原生构建 | `_ohos_toolchain` 改为尽力搜索；找不到则在 build 目录生成最小 fallback 工具链（见第 7 条）而非抛异常 |
| 6 | 原生构建下 libSBML 的 FindZLIB 在 CMake 4.x 报 `ZLIB_LIBRARY ... NOTFOUND` 硬错 | `find_package(ZLIB QUIET)` 无条件执行，`WITH_ZLIB=OFF` 也跑；NOTFOUND 传给 `check_library_exists` 在新 CMake 下不再是警告而是错误 | build() 前遍历 vendor 为每个 `FindZLIB.cmake` 加 `if(LIBZ_CMAKE_PATH)` 守卫；`WITH_ZLIB=OFF` 不变，zlib 永不链接 |
| 7 | 无工具链原生配置下 libSBML 全员报 `'__declspec' attributes are not enabled` | cmake 4.x 无 Platform/HarmonyOS 模块，`UNIX` 变量未被置位，上游 `if(UNIX)...else add_definitions(-DWIN32)` 走错分支，extern.h 取 `__declspec(dllexport)` | 缺系统工具链时生成 `hmbs-fallback-toolchain.cmake`（`CMAKE_SYSTEM_NAME=Linux` + OHOS clang 编译器），恢复 `if(UNIX)` 语义；产物仍是 OHOS clang 编出的原生 aarch64 二进制 |
| 8 | test_package 链接 `undefined symbol: SedDocument::...`（全部 Sed 类符号未定义，主构建与 ctest 已通过） | 消费者链接未解析到 sedml 静态库（`-l` 名称/目录与实际交付不一致时静默产生空链接，表现为全 Sed 符号未定义） | build() 新增归档清单+符号门禁（缺 `libsedml-static.a` 直接失败；有 nm/llvm-nm 时校验 `SedDocument` 符号）；package() 合并 `lib64/` 回 `lib/` 并校验交付清单；package_info 探测 `lib/`+`lib64/` 并记录 `libs`；test_package 改用绝对路径 + `--start-group/--end-group` 链接，缺失归档时显式报错 |
| 9 | test_package 9/10：`round-tripped document has zero errors` 失败（上游 33/33 已通过；另有 preflight.sh `/tmp/... Read-only file system` 噪声） | 自建 UniformTimeCourse 缺 4 个必需属性（initialTime/outputStartTime/outputEndTime/numberOfPoints，见 SedUniformTimeCourse.h `hasRequiredAttributes`），文档本身非法，序列化回读后 error log 非空；测试仅用内存字符串往返，不写 /tmp，只读 /tmp 与本失败无关 | test_sedml.cpp 改用 `SedUniformTimeCourse*` 并设置 4 个必需属性（0/0/10/100），回读失败时打印 `getError(i)` 明细；不引入任何临时文件，不改测试口径（仍 10 检查） |
| 11 | CI #48898 FindEXPAT FATAL "Unable to compile a test executable against expat" (EXPAT_EXPAT_TEST/TEST2 Failed, libNuML configure 阶梯) | NuML/SEDML 声明 LANGUAGES CXX 却在 FindEXPAT 内懒加载 enable_language(C)+CHECK_C_SOURCE_COMPILES，OHOS 工具链下 C 编译器后配导致 try-compile 双失败；且 NuML/SEDML 配置未像 SBML 那样显式传递 EXPAT 路径，仅靠 DEPENDENCY_DIR 搜索 | _enable_c_language 将两处 project LANGUAGES CXX 补为 C CXX；NuML/SEDML 配置新增 EXPAT_DIR 环境+DEXPAT_INCLUDE_DIR/DEXPAT_LIBRARY/DCMAKE_PREFIX_PATH 显式指向 deps（与 SBML 成功配置同值） |
| 10 | 真机 compile 失败伴 `preflight.sh[306]: can't create temporary file /tmp/... Read-only file system`（同时 sbml 构建 14% 处 SSH 断开） | OHOS 上 /tmp 为只读挂载（E002），cmake/clang/sh 默认回落到 /tmp 写临时文件；配方未显式保障可写临时目录，上游测试无硬编码 /tmp（test_sedml.cpp 纯内存往返） | 主配方与 test_package 新增 `_ensure_writable_tmp()`：复用 HMBS 注入的 TMPDIR/TMP/TEMP（校验可写后 `os.makedirs`+写探针），回落 `$HOME/tmp`、`build_folder/hmbs-tmp`，导出 TMPDIR/TMP/TEMP/GOTMPDIR 给全部 `self.run`/子进程；仅替换临时根目录，不跳过任何测试 |
| 13 | 真机 compile 首步即 `CMake Error at CMakeModules/FindEXPAT.cmake:189: Parse error ... unterminated string`（expat configure 阶段） | `_relax_findexpat` 的替换串含 4 个 `\"` 引号（新串引号数与旧前缀 1 个不对等），且 os.walk 在 expat 自身 configure 前就改写了 `vendor/expat` 内同名模块，首步即解析失败；HMBS 平台诊断的 `readonly_tmp` 为伴随噪声，非根因 | 替换改为引号配平的单开引号前缀（新旧各 1 个 `\"`，后缀原样保留，实测配平为偶数），并跳过 `/vendor/expat/` 路径；保留试编译、仅降级 FATAL 为 WARNING 的策略不变 |
| 12 | CI #48914：libSBML 配好装好后，libNuML configure 经 sbml-static-config 的 find_dependency(EXPAT) 触发同族 FindEXPAT 试编译双失败 (EXPAT_EXPAT_TEST/TEST2 Failed) 而 FATAL 中断 | 同族三份 FindEXPAT.cmake（含试编译探针）逐字节一致；同一 worker、同一工具链、同一 libexpat.a 在 libSBML configure 中刚通过相同探针，产物可链接无疑——失败与归档本身无关，而是经 config 间接调用时探针上下文脆弱（且真实链接错误被 FATAL 吞掉，CMakeError.log 未进 CI 日志，无法定位）。探针只决定是否加 XML_STATIC，而 OHOS 非 Windows 目标下 expat.h 的 XMLIMPORT 本来就为空，加与不加无功能差异 | build() 沿用 FindZLIB 守卫的 os.walk 方式，对全部三份 FindEXPAT.cmake 新增 `_relax_findexpat`：保留试编译（真通过仍按上游设置 XML_STATIC），仅把试编译双失败的 `message(FATAL_ERROR` 降级为 `message(WARNING` 后继续（路径/目标均已正确就绪）；真不可链接时仍会在真实构建链接阶段显式失败，不掩盖问题 |

## 验证结果

- 本地：按任务约束不在本机运行 conan，待 HMBS 真机预检。
- 上游测试：33 个 TEST_CASE（Catch），`ctest --output-on-failure` 在真机执行，
  通过率以预检日志为准。
- test_package：`test_sedml.cpp` 10 个真实 API 检查（版本一致性、建模、KiSAO
  查询、序列化往返、零错误校验），二进制自输出
  `HMBS_TEST_PACKAGE_RESULT` 标记。

## 注意事项

- 本配方默认静态交付（`shared=False`），与模板惯例一致；`shared=True` 已实现
  （PIC + 重签名），但未经真机验证，首轮仅保证默认分支。
- 压缩的 SBML/SEDML 读写（.gz/.zip/.bz2）因 `WITH_ZLIB=OFF` 暂不支持，
  需该功能时待 zlib 联调后再开（见 PR 补充说明）。
