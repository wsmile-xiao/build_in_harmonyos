# tvm-ffi 0.1.12 适配笔记

## 软件信息

- **名称**: tvm-ffi（Apache TVM FFI，机器学习开放 ABI/FFI）
- **版本**: 0.1.12
- **上游仓库**: https://github.com/apache/tvm-ffi
- **许可证**: Apache-2.0
- **构建系统**: CMake（C++17）
- **用途**: 稳定 C ABI + C++ API 层（Any/Object/Tensor/Function/反射/序列化），供核函数库与 DSL 跨框架复用
- **申请人**: gcw_uQ09W7jl（队伍：干）

## 版本来源审计

- 上游 release 页确认 `v0.1.12` 正式 tag（2026-06-06 发布，commit 3050b0a）。
- 配方源码：官方 GitHub tag 包
  `https://github.com/apache/tvm-ffi/archive/refs/tags/v0.1.12.tar.gz`
- SHA256（2026-09-21 实测下载 975097 字节计算）:
  `4a25fe74cc599d2aedb7e5278a5c46a63395b40f5ee6e33867ccac53bc78e1f8`
- 无个人 fork、网盘或不明镜像，符合 R39。

## 功能特性

- 稳定最小 C ABI（`include/tvm/ffi/c_api.h`，含版本宏 0.1.12 与 `TVMFFIGetVersion`）。
- C++17 API：Any/AnyView、String/Bytes、Array/Map、Shape、Tensor（DLPack 零拷贝）、Function 全局注册、反射与序列化。
- 产物：`libtvm_ffi.so`（OUTPUT_NAME tvm_ffi）、`libtvm_ffi_static.a`（OUTPUT_NAME tvm_ffi_static）、测试辅助 `libtvm_ffi_testing.so`（不安装给消费者）。
- Python 模块默认关闭（需 cython，本配方不带）。

## 依赖关系

- 无 Conan 外部依赖。dlpack 头文件为 git submodule（`3rdparty/dlpack` 指向 dmlc/dlpack 84d107b），tag 包中为空目录，配方在 `source()` 从官方 `dmlc/dlpack` v1.3 tag 拉取头文件并校验 SHA256。
- libbacktrace 同为 submodule（`3rdparty/libbacktrace`），配方以 `TVM_FFI_USE_LIBBACKTRACE=OFF` 避开，核心 backtrace 走非 libbacktrace 回退路径。
- 上游测试需 googletest v1.14.0（CMake FetchContent 拉取），构建时需要 GitHub 网络；与 conandata 源码下载同源，CI 已为 GitHub URL 自动加镜像回退。

## 构建配置

```cmake
-DTVM_FFI_USE_LIBBACKTRACE=OFF   # 子模块为空，避开 autotools 外部构建
-DTVM_FFI_USE_EXTRA_CXX_API=ON   # 默认，含 extra 序列化/反射/模块源码
-DTVM_FFI_USE_THREADS=ON         # 默认，链接 Threads
-DTVM_FFI_USE_DL_LIBS=ON         # 默认，链接 CMAKE_DL_LIBS
-DTVM_FFI_BACKTRACE_ON_SEGFAULT=ON  # 默认，保持上游行为
-DTVM_FFI_BUILD_TESTS=ON         # 必开，上游测试开关
-DTVM_FFI_BUILD_PYTHON_MODULE=OFF   # 关闭，避免 cython 依赖
-DBUILD_TESTING=ON
```

### 补丁

- `patches/0001-link-tests-statically-for-ohos.patch`（portability，仅改测试链路链接，
  未改库源码与测试用例）：`tests/cpp/CMakeLists.txt` 中 `tvm_ffi_tests` 改链
  `tvm_ffi_static`；顶层 `CMakeLists.txt` 中 `tvm_ffi_testing` 改链
  `tvm_ffi_static`；`cmake/Utils/Library.cmake` 中 `tvm_ffi_testing` 由 SHARED
  改为 STATIC。测试二进制与辅助库均为同一批 objects 的静态形态，用例数不变
 （1 个 ctest 条目，388 个 GTest），交付的 `libtvm_ffi.so` /
  `libtvm_ffi_static.a` 仍正常构建安装。

## 上游测试清点（静态审计，来自源码）

- 顶层 `CMakeLists.txt` 在 `TVM_FFI_BUILD_TESTS=ON` 时 `enable_testing()`，引入 `AddGoogleTest.cmake`，`add_subdirectory(tests/cpp/)`。
- `tests/cpp/CMakeLists.txt` 通配 `test*.cc`（24 个核心文件）与 `extra/test*.cc`（9 个文件，EXTRA_CXX_API=ON 时加入），编译为单个二进制 `tvm_ffi_tests`，经 `TVM_FFI_ADD_GTEST` 注册**恰好 1 个** ctest 条目（`DISCOVERY_MODE PRE_TEST`，`ctest -N` 计 1）。
- 二进制内 `TEST()` 宏共 **388 个**（2026-09-21逐文件正则清点：核心 275 + extra 113），`ctest --output-on-failure` 的 gtest 输出即其执行证据。
- 配方 `build()` 直接跑 `ctest --output-on-failure`（不用 `cmake.test()` 的 `make test` 包装），解析真实汇总行 `N% tests passed, M tests failed out of K` 输出 `HMBS_UPSTREAM_TEST_RESULT`（framework ctest），数字零猜测分支。
- 口径：`MANIFEST.yml` 声明 `upstream_test_total: 1`，`upstream_test_count_method: ctest_entries`（与 ctest 注册一致）；388 为二进制内部 gtest 粒度，供 PR 正文补充说明。

## test_package（消费者测试，6 断言）

`test_package/test_package.cpp` 直接用 clang++ 编译（-std=c++17 -pthread），
不走 CMake configure，同样避开 HarmonyOS 平台名问题；运行 `./test_probe`，
退出码即 6/6 证据（R34），非空壳：

1. 版本宏 `TVM_FFI_VERSION_MAJOR/MINOR/PATCH == 0/1/12`
2. C API `TVMFFIGetVersion` 返回 0.1.12
3. `AnyView view = 42` 后 `cast<int>() == 42`
4. `String{"hello"} + " world"` 比较与长度
5. `Array<int64_t>{1,2,3}` 长度 3、求和 6
6. `Shape{2,3}` 维度与取值

经 ctest 运行，二进制 `RESULT 6/6` 才退出 0；`test()` 输出
`HMBS_TEST_PACKAGE_RESULT={"executed":true,...,"discovered":6,"passedCount":6}`，
并重发 `res/upstream_test_result.json` 的上游证据（缓存命中轮次不丢失）。

## 真机失败修复记录（2026-09-21，preflight compile 失败，第二轮：改用标准工具链）

- 上一方案为何无效：上一轮把根因归为“CMakeToolchain 映射 HarmonyOS
  平台名导致编译器自检失败”，改用 OHOS SDK 官方 ohos.toolchain.cmake +
  裸 cmake（对标 assimp-5/5.4.3）。但真机预检直接失败于
  `Invalid configuration: tvm-ffi: ohos.toolchain.cmake not found`——
  预检 worker 上 profile 未配 user_toolchain、OHOS_NDK_HOME 为空、
  且 glob `/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/`
  无命中。外部 SDK 文件依赖让配方在任何 SDK 布局变化的 worker 上硬失败，
  比原来的平台警告更致命。
- 新根因判断：`System is unknown to cmake` 对纯 POSIX C++ 库只是警告级
 （知识 nng 前例：不阻止构建）；真正的编译器检测失败与 bzrtp/5.3.105
  同类——profile 把编译器钉死在 `/data/service/hnp/bin/clang(++)`，
  该文件在部分预检 worker 上缺失。同时 textparser/1.9.0 用标准
  CMakeToolchain + CMake helper 在同一预检环境通过，证明标准链路可行，
  不需要外部 SDK 文件。
- 本轮不同路线（与上一轮完全不同）：删掉 `_ohos_toolchain()` 硬依赖，
  回到官方指南 4.2 标准链路——`generate()` 用 CMakeToolchain +
  `build()` 用 CMake helper；`generate()` 内做两项加固：
  (1) bzrtp 式编译器探测补丁（conf 有文件用 conf，否则 PATH
  `shutil.which`，解决 worker 缺 clang 文件问题）；
  (2) E096 显式 `CMAKE_CXX_STANDARD=17/REQUIRED`（绕开平台未知时的
  标准特性检测失败）。TVM_FFI_* 开关、ctest 解析、res 重发、重签名保持不变；
  test_package 保持 clang++ 直连，仅把编译器查找改为
  CXX/HMBS_CXX/PATH/硬编码四级回退。
- 待 HMBS 真机预检验证。

## 真机失败修复记录（2026-09-21，preflight compile 失败，第三轮：测试二进制运行时链路）

- 本轮失败证据：构建本身成功（`tvm_ffi_objs` 各目标编译通过），失败发生在
  `build()` 内跑 `ctest --output-on-failure` 时：`tvm_ffi_tests` 启动即报大量
  `Error relocating .../build/Release/lib/tvm_ffi_tests: TVMFFI*: symbol not found`
 （含 C ABI 的 `TVMFFIErrorSetRaised`/`TVMFFIFunctionCall` 与 extra C++ 符号
  `ReprPrint`/`StructuralEqual` 等），随后 `GoogleTest/DiscoverTests.cmake`
  的 PRE_TEST 发现脚本 `execute_process` 失败，无 ctest 汇总行，配方按“无可解析
  汇总”抛 `ConanException`。
- 根因判断：上游把测试二进制与 `libtvm_ffi.so`、`libtvm_ffi_testing.so`
  全输出到 `${CMAKE_BINARY_DIR}/lib`（见 `cmake/Utils/Library.cmake` 与
  `tests/cpp/CMakeLists.txt` 的 `RUNTIME/LIBRARY_OUTPUT_DIRECTORY`），测试以
  `PRIVATE tvm_ffi_shared + tvm_ffi_testing` 动态链接；配方此前既未给构建树
  加 `$ORIGIN` RUNPATH（只依赖 CMake 默认绝对路径 build-RPATH），跑 ctest
  时也未设置 `LD_LIBRARY_PATH`，OHOS 预检环境下发现/执行 helper 没能解析到
  刚构建出的同目录 `.so`。注意报错是“同文件已加载但符号缺失”形态而非
  “library not found”，因此同步加了构建期 `nm/readelf` 探针：下轮日志将直接
  给出 `libtvm_ffi.so` 的 `NEEDED/RPATH` 与关键 C ABI 导出数，可证伪“库本身
  无符号”分支。
- 本轮改动（均在 `conanfile.py`，未改上游源码与测试，不断言删减）：
  (1) `generate()` 新增 `CMAKE_BUILD_WITH_INSTALL_RPATH=True`、
  `CMAKE_INSTALL_RPATH=$ORIGIN`、`CMAKE_BUILD_RPATH_USE_ORIGIN=True`
 （kwallet/jsoncpp/curl 在仓先例），让构建树二进制自带 `$ORIGIN`；
  (2) `_run_upstream_ctest` 在 `subprocess.run` 前把 `<build>/lib`（及 `<build>`）
  前置进 `LD_LIBRARY_PATH`（babl 在 OHOS 上已验证 loader 认该变量），覆盖
  ctest 与 PRE_TEST 发现子进程；
  (3) 新增 `_log_just_built_lib_exports()`（仅日志，从不使构建失败），打印
  `lib/` 内容、`readelf -d` 的 NEEDED/RPATH 与 `nm -D` 关键符号命中数。
- 待 HMBS 真机预检验证。

## 真机失败修复记录（2026-09-21，preflight compile 失败，第四轮：测试链路改静态链接）

- 前次不同策略及其结果：第三轮按“运行时解析失败”假设，同时加了构建树
  `$ORIGIN` RUNPATH（`CMAKE_BUILD_WITH_INSTALL_RPATH` +
  `CMAKE_INSTALL_RPATH=$ORIGIN`）与 ctest 子进程 `LD_LIBRARY_PATH=<build>/lib`
  前置。本轮回来的失败指纹与上一轮逐行一致（同一批 `TVMFFI*` /
  `ReprPrint` / `StructuralEqual` 重定位缺符号，随后 PRE_TEST 发现脚本失败，
  无 ctest 汇总行），说明该假设未命中：加载器侧的两种解析手段均未改变结果。
- 本轮换路线（与上一轮完全不同）：不再修补运行时解析，改为让测试链路彻底
  不再依赖运行时 `.so`——新增 conandata 补丁
  `patches/0001-link-tests-statically-for-ohos.patch`（`git apply --check`
  已在本机对 v0.1.12 源码验证通过），三处均为链接对象替换：
  (1) `tests/cpp/CMakeLists.txt`：`tvm_ffi_tests` 由 `tvm_ffi_shared` 改链
  `tvm_ffi_static`；(2) 顶层 `CMakeLists.txt`：`tvm_ffi_testing` 由
  `tvm_ffi_shared` 改链 `tvm_ffi_static`；(3) `cmake/Utils/Library.cmake`：
  `tvm_ffi_testing` 由 SHARED 改为 STATIC，避免可执行文件静态链一份、
  testing 共享库再拖一份 shared 造成的双份全局注册表（ODR）风险。
  静态与共享来自同一 `tvm_ffi_objs`，388 个 GTest 与 1 个 ctest 条目不变，
  无断言删减；交付的 `libtvm_ffi.so` / `libtvm_ffi_static.a` 照常构建安装。
- 配套：保留第三轮的 RUNPATH/LD_LIBRARY_PATH（无害）；探针升级为必带 verdict
  并追加进 ctest 失败异常信息，即使日志被摘要也能看到
  `artifacts/NEEDED/key_hits` 机器证据；`manifest.yaml` 登记补丁。
- 待 HMBS 真机预检验证。

## 真机失败修复记录（2026-09-21，preflight compile 失败，第五轮：补上缺失的 apply 调用）

- 前次不同策略及其结果：第四轮新增静态链接补丁并在本机 `git apply --check`
  验证通过，但本轮失败指纹仍逐行一致；且本轮摘要首次带回了探针 verdict：
  `artifacts=3 lib_dynsym=94 key_hits=6/4`（共享库本身 94 个动态符号、关键
  C ABI 全部导出，库是好的），而测试二进制 `NEEDED=[../../lib/libtvm_ffi_testing.so,
  ../../lib/libtvm_ffi.so, ...] RUNPATH=[]`——补丁根本没生效，二进制仍动态
  链接。
- 根因（配方 bug，非上游问题）：`export_conandata_patches()` 只把 `.patch`
  文件导出到缓存，真正打补丁需要 `apply_conandata_patches(self)`；配方从未
  调用它。证据：预检 `Exporting` 段明确 `Copied 1 '.patch' file`（仅导出），
  真机 readelf 显示测试二进制仍带 `libtvm_ffi.so` NEEDED。
- 本轮改动（与上一轮完全不同维度：上一轮是补丁内容，本轮是补丁生效机制）：
  `conanfile.py` 导入 `apply_conandata_patches` 并在 `build()` 开头、
  `cmake.configure()` 之前调用——与仓内 abseil/ableton-link/abpoa 等 6 个
  CMake 配方的既有模式一致。补丁文件本身、`conandata.yml` 登记不变。
- 待 HMBS 真机预检验证（预期测试二进制不再有 `libtvm_ffi*.so` NEEDED，
  verdict 行可直接证实）。

## 验证命令（真机，HMBS 后台执行）

```bash
cd archives/t/tvm-ffi/0.1.12
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

预期日志包含：
`HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"ctest",...}` 与
`HMBS_TEST_PACKAGE_RESULT={"executed":true,...,"discovered":6,"passedCount":6}`。
实际通过率以真机预检日志为准，本轮尚未验证。

## 参考资料

- https://github.com/apache/tvm-ffi
- https://github.com/apache/tvm-ffi/releases/tag/v0.1.12
- https://tvm.apache.org/ffi/
- 本仓参考：archives/t/textparser/1.9.0（ctest 证据标记与 res 重发模式）

## 真机失败修复记录（2026-09-21，preflight compile 失败，第六轮：连接中断加固串行与超时）

- 本轮失败证据：静态链接补丁已生效——探针 verdict 显示测试二进制
  `NEEDED=[libc++_shared.so, libc.so]`（不再有 `libtvm_ffi*.so`），
  `lib_dynsym=94 key_hits=6/4`（共享库本身符号完整）。但随后
  `Connection to 47.242.172.160 closed by remote host`，上游 0/0/0，
  无任何 HMBS 标记。说明失败点已从“测试二进制解析”后移到
  “ctest 执行阶段 SSH 会话中断”，配方在中断前未来得及写标记。
- 根因判断：ctest 命令无单用例超时、无串行约束（`ctest --output-on-failure`
  裸跑 388 个 gtest），单个在 OHOS 上挂起的用例会拖住整个 SSH 会话；
  主构建也未显式串行。库本身与测试链路均已就绪，属执行韧性问题，
  非上游源码问题，不断言删减、不跳过测试。
- 本轮改动（均在 `conanfile.py`，测试口径不变）：
  (1) `cmake.build(build_tool_args=["-j1"])`（baloo/6.28.0 在仓先例，
  HMBS jobs=1 纵深防御），锁定单进程内存峰值；
  (2) ctest 改为 `ctest --test-dir <build> --output-on-failure -j1 --timeout 120`
  并置 `CTEST_PARALLEL_LEVEL=1`，挂起用例转为明确失败而非 SSH 中断；
  (3) 上游解析、res 重发、探针 verdict、静态补丁均保持不变。
- 待 HMBS 真机预检验证。

## 真机失败修复记录（2026-09-21，preflight compile 失败，第七轮：降一档优化削峰）

- 前次不同策略及其结果：第六轮按“ctest 阶段 SSH 挂起”假设，加了主构建
  `-j1` 串行与 `ctest -j1 --timeout 120`。本轮回来的中断点提前到构建期
  96%（`extra/test_structural_key.cc.obj` 编译中 `Connection closed`），
  根本没走到链接/探针/ctest——上一轮假设未命中，串行 alone 不够。
- 本轮换路线（与上一轮完全不同维度：上一轮是执行期串行+超时，本轮是
  编译期单 TU 峰值）：`generate()` 新增
  `CMAKE_C/CXX_FLAGS_RELEASE="-O2 -DNDEBUG"`（Release 默认 -O3 降一档，
  NDEBUG 与其他语义保留，翻译单元集合不动；libobjcryst/2022.1.4 在仓先例）。
  模板重的测试 TU 在 -O3 下单进程内存峰值最高，-O2 直接压低优化器峰值；
  与已有的 `-j1` 串行叠加锁定整机峰值。交付语义不变，无断言删减。
- `manifest.yaml` 的 `configure_options` 同步登记新增两项。
- 待 HMBS 真机预检验证。

## 真机失败修复记录（2026-09-21，preflight 上游测试失败，第八轮：静态链路补 whole-archive）

- 本轮失败证据：构建与链接已通，ctest 真实跑起来并输出汇总
  `93% tests passed, 27 tests failed out of 387`（discovered=387 executed=387
  passed=360 failed=27），失败集中在 `Reflection.AutoInit*`（9）、
  `StructuralEqualHash.*`（7）、`FindAccessPaths.*`（6）及 `Array.Contains`、
  `AccessPathRepr.StreamlinedFormat`、`StructuralKey`、`VisitErrorContext` 各 1，
  外加兜底项 `tvm_ffi_tests (SEGFAULT)`。此前“无汇总、PRE_TEST 发现失败”已消失，
  说明静态链接确实解决了 loader 解析问题；27 失败是新暴露的执行期问题。
- 根因判断：静态归档默认只拉取被符号引用的成员，测试二进制以字符串名
  （`Function::GetGlobalRequired("ffi.ArrayContains")`、反射类型名）查找的
  `TVM_FFI_STATIC_INIT_BLOCK` 注册块（`src/ffi/container.cc` 的全局函数注册、
  `src/ffi/testing/testing.cc` 的全部测试类型注册）若所在 `.o` 未被引用就会被
  丢弃，注册静默丢失。证据：失败项恰好是依赖 testing.cc/容器全局注册的子集
  （360 项纯头文件用例全过）；`testing_object.h` 的 `RegisterReflection()` 为
  内联需显式调用，而 `TestCxxAutoInit*` 等类型仅在 testing.cc 定义、测试以
  字符串查表访问，链接器看不到符号引用。原 SHARED 形态下所有 initializer 常驻，
  故上游 CI 常过；改 STATIC 后未加 whole-archive 即引入此语义差。
- 本轮改动（不断言删减、不跳过测试）：补丁在 `tests/cpp/CMakeLists.txt` 的
  `tvm_ffi_tests` 链路追加 `LINKER:--whole-archive,$<TARGET_FILE:tvm_ffi_static>,
  $<TARGET_FILE:tvm_ffi_testing>,--no-whole-archive`（UNIX 非 Apple 生效），
  把静态核心与测试辅助整体拉入可执行文件，还原共享库“全部 initializer 运行”
  语义；`conanfile.py` 文档注释同步。另修正 `test_package/MANIFEST.yml`：
  PRE_TEST 发现时把 1 个 add_test 展开为 387 个可用 ctest 条目
  （388 个 TEST 宏减 1 个 DISABLED），`upstream_test_total` 由 1 改为 387，
  口径仍为 `ctest_entries`，与真机汇总行一致。
- 待 HMBS 真机预检验证（预期 387/387 通过；若仍有残留失败，需按真实 gtest
  输出逐项归因，不凑数字）。

## 真机失败修复记录（2026-09-21，preflight 上游测试失败，第九轮：核实 whole-archive 修复并最小加固）

- 本轮输入与第八轮同一失败指纹（`93% tests passed, 27 tests failed out of 387`，
  `Reflection.AutoInit*` 9 项、`StructuralEqualHash.*` 7 项、`FindAccessPaths.*` 6 项、
  `Array.Contains`/`AccessPathRepr.StreamlinedFormat`/`StructuralKey`/
  `VisitErrorContext` 各 1，另 `tvm_ffi_tests (SEGFAULT)` 兜底项，共 27）。
  该次运行用的是第七轮代码（静态链路、无 whole-archive）；第八轮的 whole-archive
  改动已在工作树但尚未经过真机验证，本轮即为其验证轮。
- 根因复核（逐项对照上游 v0.1.12 源码原文确认，非猜测）：27 项全部依赖
  `src/ffi/testing/testing.cc` 内 `TVM_FFI_STATIC_INIT_BLOCK` 注册块——
  `TestCxxAutoInit(Obj|Simple)` 等自动初始化类型（AutoInit* 失败项）、
  `TestCompareObj/TestHashObj` 等结构比较类型（StructuralEqualHash* 失败项）、
  `testing.*` 全局函数（`ffi.ArrayContains`、`ffi.GetKwargsObject` 等）——
  測試均以字符串名查表（`GetGlobalRequired`/反射类型名），链接器看不到符号引用；
  testing 改 STATIC 后若无 whole-archive，这些 `.o` 成员即被丢弃，注册静默丢失。
  360 项通过的是纯头文件/核心对象用例，与该假设一致；SEGFAULT 兜底项为同一
  二进制全量跑，大概率是缺失注册导致空查表后解引用的次生崩溃，同源。
- 本轮核实结论：第八轮三处 `replace_in_file` 的查找串已用
  `raw.githubusercontent.com/apache/tvm-ffi/v0.1.12` 原文逐字校验——
  顶层 `CMakeLists.txt` 的 `target_link_libraries(tvm_ffi_testing PRIVATE tvm_ffi_shared)`、
  `cmake/Utils/Library.cmake` 的 `  add_library(${target_name}_testing SHARED)`（两空格缩进）、
  `tests/cpp/CMakeLists.txt` 的 `target_link_libraries(tvm_ffi_tests PRIVATE tvm_ffi_shared)`——
  与上游完全一致，`strict=True` 下能命中，无需改动查找逻辑。
- 本轮唯一改动（`conanfile.py`，零语义变化、不断言删减、不跳过测试）：三次替换后加一行
  `self.output.info("tvm-ffi: test chain statically linked ...")`，让下轮预检日志直接证明
  静态化+whole-archive 编辑已生效（若仍残留失败，可凭此行区分“补丁未生效”与“真 OHOS 不兼容”）。
- 待 HMBS 真机预检验证（预期 387/387 通过；若有残留，按真实 gtest 输出逐项归因并填 gaps，不凑数字）。

## 真机失败修复记录（2026-09-21，preflight 上游测试失败，第十轮：whole-archive 平台守卫失效）

- 前次不同策略及其结果：第八轮加 `--whole-archive`（UNIX 非 Apple 守卫）、第九轮逐字核对
  查找串并加生效确认日志。12:30 预检（recipe 行号 248->253、462->467 证明已含这两轮改动）
  结果与 12:06 逐项一致：同 27 项、同名单、同 48 秒耗时。whole-archive 改动对结果零影响，
  说明它在真机根本没生效，而非“注册假设”本身被证伪——必须换策略，不得重复加 flag。
- 新根因判断（与上轮完全不同维度：上轮修 flag 内容，本轮修 flag 守卫）：测试链路追加的
  `if(UNIX AND NOT APPLE)` 在 OHOS 上恒为假。证据链：(1) 预检日志明示
  `System is unknown to cmake, create: Platform/HarmonyOS`——stock CMake 无 HarmonyOS
  平台模块，UNIX/APPLE/WIN32 等平台变量均未置位（本配方 E096 条目早已记录平台未知导致
  的特性检测问题，同源）；(2) 两次预检失败指纹字节级一致，若 flag 生效至少应改变部分
  结果；(3) 上游 `ffi.ArrayContains`（`src/ffi/container.cc` 静态注册块，本轮已取原文核实）
  这类核心全局函数仍报缺失，与“静态归档丢成员且 whole-archive 未执行”完全吻合。
- 本轮改动（`conanfile.py`，仅改守卫，不断言删减、不跳过测试）：`tests/cpp/CMakeLists.txt`
  注入块的 `if(UNIX AND NOT APPLE)` 改为 `if(NOT MSVC)`（MSVC 由编译器 ID 判定，不受平台
  模块缺失影响；本配方 validate 仅允许 Linux/OHOS clang，LINKER:--whole-archive 恒有效，
  MSVC 需 /WHOLEARCHIVE 故保留排除）。注释同步记录守卫原因。
- 待 HMBS 真机预检验证：若 27 项消失则假设闭环；若部分残留，按真实 gtest 输出逐项归因
  并填 gaps，不凑数字；若仍字节级一致，则升级为 object-library 直链等不依赖链接器 flag
  的方案。

## 真机失败修复记录（2026-09-21，preflight compile Signal 9，第十一轮：加深削峰到 -O1 -g0）

- 本轮失败证据：真机 `failed / compile / Signal 9`，stdout/stderr 均为空，
  上游 0/0/0、无 HMBS 标记。上一轮（第十轮）刚把测试链路守卫改为
  `if(NOT MSVC)` 使 `--whole-archive` 在 OHOS 上真正生效，静态全量链接
  直接抬高单进程链接峰值；此前的 `-O2 + -j1` 组合在未加 whole-archive 时
  已处临界（第七轮 96% 编译 `extra/test_structural_key.cc.obj` 处中断），
  本轮 Signal 9 即 OOM-killer 特征（Signal 9 = SIGKILL），与编译/链接峰值
  一致，而非源码错误。
- 根因判断：模板重的测试 TU（structural/serialization）在 -O2 下优化器
  峰值仍超受限 worker 上限，叠加 whole-archive 链接需一次性保留全部
  `.o`（含 `src/ffi/testing/testing.cc` 注册块与容器注册块），单进程峰值
  再上一个台阶。不断言删减、不跳过测试、不动测试口径。
- 本轮改动（`conanfile.py` + `manifest.yaml`，仅编译期峰值）：
  `CMAKE_C/CXX_FLAGS_RELEASE` 由 `-O2 -DNDEBUG` 加深为
  `-O1 -DNDEBUG -g0`（NDEBUG 与翻译单元集合不动，优化语义对测试结果
  无影响；`-g0` 同时砍掉调试信息，缓解编译与链接双端峰值）。
  `-j1` 串行、`--whole-archive`（NOT MSVC 守卫）、ctest `-j1 --timeout 120`、
  RUNPATH/LD_LIBRARY_PATH、探针 verdict 均保持不变。
- 待 HMBS 真机预检验证（预期编译通过并跑出 387/387；若仍 Signal 9，
  下一步按真实日志区分编译期 TU 与链接期，再考虑测试目标级 -O0 或
  分步构建，不凑数字）。

## 真机失败修复记录（2026-09-22，preflight compile OOM，第十二轮：测试目标级 -O0 + 分阶段串行）

- 本轮失败证据：真机 `failed / compile / sh: /storage/Users/currentUser/.harmonybrew/bin/rm: Out of memory`，上游 0/0/0、无 HMBS 标记。连 `rm` 都无法 fork/exec（ENOMEM），说明不是单个源码错误，而是整机内存耗尽背景下的编译峰值问题。上一轮（第十一轮）已是全局 `-O1 -DNDEBUG -g0` + `-j1`，本轮若原样再降全局优化等级即重复同一策略族，必须换路线。
- 根因判断：模板重的测试 TU（`extra/test_structural_key.cc` 等 33 个测试文件）在 -O1 下单进程优化器峰值仍超受限 worker 上限；叠加 `--whole-archive` 测试链接需一次性保留全部 `.o`（含 `src/ffi/testing/testing.cc` 注册块），单次 `cmake --build -j1 all` 把编译峰值与链接峰值压在同一个调用内，OS 来不及回收。`rm` OOM 即该背景下的 fork 失败表象。
- 本轮改动（与第十一轮完全不同维度：上轮是全局 Release 优化等级，本轮是目标级 + 分阶段，交付库语义不动，不断言删减、不跳过测试、不动测试口径）：
  (1) `tests/cpp/CMakeLists.txt` 注入 `target_compile_options(tvm_ffi_tests PRIVATE -O0 -g0)`（经 `tvm_ffi_add_gtest` 锚点追加，clang 以最后 -O 为准，target 选项排在 `CMAKE_CXX_FLAGS_RELEASE` 之后，故仅测试目标降到 -O0，交付的 `libtvm_ffi.so` / `libtvm_ffi_static.a` 仍保持全局 -O1 -g0）；
  (2) `build()` 改为分阶段串行：先 `--target tvm_ffi_static -j1`，再 `--target tvm_ffi_shared -j1`，最后不带 target 的 `-j1` 构建剩余（testing + tests + whole-archive 链接），每阶段峰值独立、阶段间由 OS 回收；
  (3) 全局 `-O1 -DNDEBUG -g0`、`-j1`、`--whole-archive`（NOT MSVC 守卫）、ctest `-j1 --timeout 120`、RUNPATH/LD_LIBRARY_PATH、探针 verdict 均保持不变。
- 待 HMBS 真机预检验证（预期编译通过并跑出 387/387；若仍 OOM，下一步按真实日志区分编译期 TU 与链接期，再考虑测试辅助库目标级 -O0 或单 TU 拆分，不凑数字）。

## 真机失败修复记录（2026-09-22，preflight 上游测试解析失败，第十三轮：汇总行缺失改逐行解析）

- 本轮失败证据：构建与测试执行已通（日志见数百行 346/389 Test Passed 及静态链路 verdict test NEEDED 仅剩 libc，无 loader 缺符号），但配方抛 no parseable summary 并输出 discovered=0/executed=0。旧解析器只认 ctest 人类汇总行，汇总行缺失即判 0/0/0，把真实进度全部丢掉。
- 根因判断：解析器脆弱性，非上游源码问题。静态链路 + whole-archive（NOT MSVC 守卫）+ 测试目标 -O0 + 分阶段 -j1 均已生效；失败点是证据提取层把汇总行缺失等同于测试没跑。另探针 key_hits=6/4 为行计数 bug（同一符号多行），非库缺符号。
- 本轮改动（conanfile.py，不断言删减、不跳过测试、不动测试口径）：(1) _run_upstream_ctest 改为确定性双源：post-build ctest -N 的 Total Tests 拿 discovered，逐行扫描含 Test # 的输出按 Passed/Failed|Timeout/Not Run|Skipped|Disabled 分类计数，汇总行仅做交叉日志；无 Test # 行时回退读 Testing/Temporary/LastTest.log（搜过路径如实记录），仍无证据才报失败且 discovered 取 ctest -N 而非 0；恒等式自检；(2) 探针 key_hits 改为去重计数；(3) MANIFEST/pr-body 上游总数 387->389（最新预检多行 .../389，配方运行时以 ctest -N 为准）。
- 待 HMBS 真机预检验证（预期 389/389 通过；若部分失败/中断，新标记将给出真实计数，下轮按行归因填 gaps）。

## 真机失败修复记录（2026-09-22，preflight 上游测试中途中断，第十四轮：执行侧加固与 kill 点定位）

- 本轮失败证据：上轮逐行解析器生效，首次给出真实计数 discovered=389 executed=288 passed=288 failed=0 skipped=2，无汇总行。0 失败但 99 个用例无结果行，说明 ctest 在约 290/389 处被 runner 侧终止（OOM/SIGKILL/磁盘），而非测试失败；上轮只改解析层，本轮按要求换执行侧策略。
- 根因判断：单次 ctest 长跑在受限 worker 上被杀；旧实现用 capture 的 subprocess.run，无流式落盘、无 core 限制、无 kill 点信息。测试口径与总数 389（ctest -N）无误，不动。
- 本轮改动（conanfile.py，同一条 ctest 命令、同一口径，不断言删减、不跳过测试）：(1) Popen+communicate 合并 stderr，超时保留 TimeoutExpired.stdout 真实前缀并落盘 ctest_stream.log；(2) posix preexec_fn 置 RLIMIT_CORE=0，崩溃用例仍记 Failed 但不写巨型 core 撑爆磁盘（第 8 轮已有 SEGFAULT 前科）；(3) 结果行锚定 N/M Test #K 前缀分类，杜绝回显文本污染计数；(4) 不完整运行必读增量写入的 LastTest.log 佐证并在 reason 上报最后完成的 Test #K；(5) 恒等式改显式门禁，违例仍带原始计数输出 marker 再抛错。
- 待 HMBS 真机预检验证（若再次中断，新 reason 将直接给出 kill 点测试号与 LastTest 佐证，下轮可针对该测试定点归因填 gaps）。

## 真机失败修复记录（2026-09-22，preflight 完成但误判失败，第十五轮：LastTest 主源对账 + 下载镜像）

- 本轮失败证据：上轮执行侧加固生效，日志首次同时给出双源：stdout 扫描 passed=387 skipped=2（last Test #389），LastTest.log passed=389 failed=0 skipped=0，ctest -N=389，key_hits=4/4，NEEDED 仅剩 libc。全部 389 个用例实际已跑完且无失败，但因汇总行缺失 + 2 个扫描 skip 幻影被判 failed。另本轮 source() 出现 github 直连 ConnectTimeout（重试后成功），命中下载超时例外规则。
- 根因判断（与上轮执行侧策略不同维度）：(1) 证据口径问题：stdout 扫描把 2 行非结果行误计为 skip（点前导锚定仍不够，状态词须跟在点线之后才算），而 ctest 自身记录 LastTest.log 是干净的 389/0/0；(2) 下载可靠性：github 直连抖动，需复用 build_and_test.sh 的 gh-proxy 映射。
- 本轮改动：(1) conanfile 对账规则：LastTest.log 总数等于 ctest -N 时以它为唯一每用例来源、stdout 扫描仅佐证（含分歧时打印被折扣的 skip 行原文），否则沿用扫描 + kill 点 reason；扫描状态须跟在点线后，消除幻影分类；(2) conandata.yml 两处 url 改为有序列表（gh-proxy.com 镜像在前、官方在后，sha256 不变），与 build_and_test.sh 的 GitHub 映射一致；不断言删减、不跳过测试。
- 证伪说明：该 harness 曾在第 8 轮如实报出 27 个失败，用例非空比空；本轮每用例约 0.1s 真实执行，389 全过可信。
- 待 HMBS 真机预检验证（预期 marker 为 status passed、389/389/0/0）。


## CI 失败修复记录（2026-09-23，CI #56404 上游计数门禁，第十六轮：单源计数+DISABLED gaps）

- 本轮失败证据：CI #56404 构建本身全过（387 passed + 2 Disabled Not Run，0 failed，约19.8s），但配方抛 identity gate：executed=389 > discovered=387。日志行：scan passed=387 failed=0 skipped=2，LastTest.log passed=389 skipped=0，summary out of 387，ctest -N应为389。
- 根因：双源冲突+总数误用摘要。(1) LastTest.log 的 ^Test Passed. 计数把2个Disabled也计为Passed（Disabled在LastTest.log中无Not Run块），总数389与扫描387+2不一致；旧规则在lt_total==ctest -N时整体采用LastTest.log，用389覆盖扫描。(2) discovered误用人类摘要387（摘要天然排除Disabled/Not-Run），导致executed 389 > discovered 387。两者叠加触发门禁，非上游源码问题。
- 本轮改动（conanfile.py，不断言删减、不跳过测试）：(1) LastTest.log降为佐证，扫描非空时永不覆盖，仅在零行时回退；分歧只打日志；(2) discovered唯一源改为post-build ctest -N，摘要仅交叉日志；(3) ok条件改为failed==0且executed+skipped==discovered，2个上游DISABLED以gaps environment如实上报（387/389），status passed；(4) test_package重发门禁同步放宽为failed==0且passed==executed且executed+skipped==discovered。
- 待HMBS真机预检验证（预期387 passed + 2 skipped gaps，discovered 389）。

## 真机失败修复记录（2026-09-23，preflight compile 失败，第十七轮：vendored googletest 离线化 FetchContent）

- 本轮失败证据：真机 `failed / compile`，`cmake.configure()` 内上游 `cmake/Utils/AddGoogleTest.cmake` 的 `FetchContent` 对 `https://github.com/google/googletest.git` 三次 `git clone` 均 `Failed to connect to github.com:443 after ~65s`，随后 `Build step for googletest failed`，配置中断，上游 0/0/0。构建链本身（toolchain 补丁、编译器探测）已过，失败点是测试框架的 configure 期网络下载，与库源码无关。
- 根因判断：上游写死 `GIT_REPOSITORY ...googletest.git` + `GIT_TAG v1.14.0`，预检 worker 无 github.com:443 直连；此前十六轮全部聚焦编译/链接/解析层，从未动过该下载路径，本轮是新暴露的失败域，必须换路线。
- 本轮改动（不删减断言、不跳过测试、不动测试口径）：
  (1) `conandata.yml` 新增 `googletest` 条目（v1.17.0 tarball，gh-proxy 镜像在前、官方在后，sha256 与仓内 `gtest/1.17.0.1` 配方同值，不为镜像改校验值）；框架升级只换测试运行器，不改任何上游用例；
  (2) `source()` 新增拉取并校验该包到 `googletest-src/`（与上游树并列，上游 glob 扫不到），附带与 `gtest/1.17.0.1` 同源的 OHOS TMPDIR 沙箱补丁；
  (3) `generate()` 置 `FETCHCONTENT_SOURCE_DIR_GOOGLETEST` 指向该目录（FetchContent 官方离线变量），上游 `AddGoogleTest.cmake` 零修改，clone 步骤整体跳过。
- 待 HMBS 真机预检验证。
