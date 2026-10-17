# liblas 1.8.1.r145 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: clang/clang++ (HarmonyOS aarch64, 真机预检)
- 状态: built (待真机预检)

## 版本说明
- 上游 1.8.1 为 2016-08-23 正式 release, 之后 master 持续修复
  (GDAL/C++ 标准等兼容性修复)。
- 本次采用 r145 快照, 对应 commit 33097f17e27b853ac7b9651025a70354ffb10cfc
  (Merge PR #232, cmake: avoid downgrade CXX_STANDARD with GDAL),
  与 Arch Linux `1.8.1.r145+g33097f17` 同源。
- 源码包: `https://github.com/libLAS/libLAS/archive/<commit>.tar.gz`
  (sha256 已实测: e18caf31..., 10.7MB)。

## 编译步骤
1. `conan create archives/l/liblas/1.8.1.r145 -pr=ohos-aarch64`
2. CMake 配置要点:
   - `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` (上游 `cmake_minimum_required(2.8)`,
     CMake 4 需 legacy-policy 垫片, 同 libkml 做法)
   - `-DBUILD_SHARED_LIBS=OFF` (默认静态, 需补丁让上游尊重该变量)
   - `-DWITH_UTILITIES=OFF -DWITH_GDAL=OFF -DWITH_LASZIP=OFF`
     `-DWITH_GEOTIFF=OFF -DWITH_TESTS=ON -DBUILD_OSGEO4W=OFF`
   - Boost 走经典 Find 模块, 用 cache 变量显式指向
     Conan 包目录 (同 libkml 做法, config-mode 不适用)。
3. `cmake --build`, 随后 `ctest --output-on-failure` 运行上游
   `liblas_test` (TUT 套件, 输入为 `test/data/*.las`)。
4. `cmake --install` 产出 `liblas.so/liblas_c.so`(或静态) + 头文件。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `add_library(las SHARED ...)` 硬编码, `BUILD_SHARED_LIBS=OFF` 无效 | 2016 年写法, 未参数化 | 新增 `0001-respect-build-shared-libs.patch`, 去掉硬编码 `SHARED`, 由 `BUILD_SHARED_LIBS` 控制 |
| 2 | CMake 4 配置失败: `Compatibility with CMake < 3.5 has been removed` | 上游 `cmake_minimum_required(VERSION 2.8.11)` | `CMAKE_POLICY_VERSION_MINIMUM=3.5` (libkml 同款) |
| 3 | 依赖链过重 (GDAL/PROJ/Utilities) | 全开会引入 gdal + proj 全链 | 默认关闭 GDAL/LASzip/Utilities, 仅保留 GeoTIFF (上游默认 ON) + Boost + TIFF, 路径 A 最小闭包 |
| 4 | 真机预检报 `[readonly_tmp]` (/tmp 只读, `can't create temporary file /tmp/...: Read-only file system`), 首个失败叶子为 conancenter bzip2/1.0.8 的 CMake 编译器校验 | 真机 /tmp 只读, 构建/测试临时文件须走 HMBS 注入的可写 TMPDIR；本配方此前未显式约束临时目录 | 主配方与 test_package 新增 `_build_environment()` (优先 HMBS 注入的 TMPDIR/TMP/TEMP, 回退 build-folder/tmp), `build()/package()/test()` 全程套用；仅替换临时文件根目录，不跳过任何上游测试；依赖版本与测试口径不变 |
| 5 | 上轮 TMPDIR 包裹后同一指纹第 2 次失败：仍停在 conancenter bzip2/1.0.8 的 `System is unknown to cmake` + `CMAKE_C_COMPILER` 中断；新日志证明依赖图走的是 conancenter 配方 (proj/9.3.1 而非站内 libgeotiff 所需的 9.3.1.1)，且本配方缺失门禁要求的两行 JSON 标记 | 同版本依赖存在 remote 竞争，conancenter 修订抢占配方解析，其 CMake 构建在 OHOS 上系统性不可用；TMPDIR 包裹只能约束本包动作，无法修复依赖构建；标记缺失则即使构建转绿也会被判 incomplete | 换路线切依赖图 (非重复调参)：boost/1.91.0→1.91.0.1.3 (站内后缀、conancenter 无收录、含 serialization、零依赖)，WITH_GEOTIFF ON→OFF 并删除 libgeotiff/libtiff 依赖 (上游 OFF 时跳过 TIFF/JPEG/ZLIB 查找)；补齐 `HMBS_UPSTREAM_TEST_RESULT` (ctest LastTest.log 实测解析，失败闭环) 与 `HMBS_TEST_PACKAGE_RESULT` (8/8，运行码定通过与否) 双标记及 cache 命中重发；主配方与 test_package 增加编译器可用性兜底 (仅替换缺失路径)。测试口径：上游 GeoTIFF 门控用例按上游条件编译排除 (MANIFEST 已注明)，其余 TUT 不变；test_package 第 8 项断言改为期望 GeoTIFF=false |
| 6 | 切图后失败点推进到本包自身 `build()`：`apply_conandata_patches` 报 `0001` 补丁 `source file is different - src/CMakeLists.txt` (actual 首行 `set(LIBLAS_CPP`) | 补丁 hunk 头行号写错 (`@@ -110,8`，而真实 `add_library` 在 218-219 行)，conan 严格打补丁时在 110 行附近找不到上下文；源码本身无误 (sha256 与实测一致) | 重写补丁 hunk 为 `@@ -211,12 +211,12 @@` (以 WIN32 块为前置上下文)，已用 sha256 校验过的真实源码包做端到端应用验证 (旧边 12 行逐行命中、新边去掉 SHARED)；补丁文件名/类型/描述不变 |
| 7 | 补丁行号修正后仍 compile 失败：project() 报 CMAKE_C_COMPILER 为 /data/service/hnp/bin/clang 中断（CXX 曾触发 fallback 到 harmonybrew），conandata 手写 gh-proxy 镜像触 PF7 | 上一周期假设 profile 绝对路径缺失则 PATH 找 clang 替代有效，但新日志证伪：C 编译器未被修复仍用原坏路径，CXX 即便换成宿主 clang 也缺 OHOS sysroot/flags，配方侧探测与 CMakeToolchain 冲突；libkml/1.3.0 无兜底可直接构建为证；gh-proxy 手写违反 review-memory 明禁（CI 自动叠加镜像） | 换路线做减法（非重复调参）：删除主配方/test_package 的 _discover_compiler/_repair_cmake_toolchain/CC-CXX 注入，编译器回归 profile+CMakeToolchain 权威（同 libkml）；_build_environment 保留纯 TMPDIR/TMP/TEMP 重定向（readonly_tmp 合法处理）；conandata 删除 gh-proxy 行只留官方 URL，sha256 不变；保留依赖切图、双 JSON 标记、补丁行号修正 |
| 8 | 同一指纹第2次：删除回退后失败完全相同（回退 warning 消失，CMAKE_C/CXX_COMPILER 仍报 hnp 路径中断），证伪“回退是病因”假设 | 新证据链：hnp 路径在本预检 worker 上根本不存在（libcacard 有 Errno 2 实证）；cache_variables/-D 换不掉 CMakeToolchain 钉死的编译器（libesmtp 实证）；cmake 4.4.3 无 Platform/HarmonyOS（libmacaroons/libsodium 实证）；首轮回退失败另有机制（只修了 CXX 或 cache 被钉死） | 换路线修工具链文件本身（非 -D/非 cache）：主配方与 test_package 在 build() 的 cmake.configure() 前重写 conan_toolchain.cmake 中已不存在的编译器路径，替换值经 --version 实测（conf 可用优先→PATH→同目录 sibling→HNP/SDK），可用路径永不触碰、无可用时保留原错不掩盖；不跳过任何检查；另自测发现并修复替换模板在反斜杠路径下的 bad escape，改用 lambda 拼接 |
| 9 | 工具链修复生效（日志出现 HMBS toolchain repair，双编译器指向 harmonybrew cc/c++，configure 通过并进入 cmake.build），新失败点为编译期 `boost/uuid/uuid.hpp file not found`（header.hpp:46，经 index/reader 链） | configure 能过而编译缺头文件，说明 find_package(Boost) 未给出可用 Boost_INCLUDE_DIRS：站内 boost 包无 CMake config，CMake 4.x 的 config 偏好（CMP0167）使模块模式旁落，Inline 的 Boost_INCLUDE 提示被覆盖或落空；libasd 有同类老 CMake+Boost 在 CMake 4.x 下的设备实测解（BOOST_ROOT+CMP0167=OLD，6/6 过） | generate() 新增三行且仅三行：BOOST_ROOT/Boost_ROOT 指向 boost 包目录，CMAKE_POLICY_DEFAULT_CMP0167=OLD 强制 FindBoost 模块模式；保留原有 Boost_INCLUDE 三行（libkml 同款，双保险）；不碰测试开关与测试口径 |
| 10 | 上轮 BOOST_ROOT 双拼写补丁后 configure 直接中断：`FindBoost.cmake:871 ERROR: Boost_ROOT is not the correct spelling. The proper spelling is BOOST_ROOT` (CallStack _Boost_CHECK_SPELLING) | 上轮假设大小写两行双保险被新日志证伪：CMake>=3.12 FindBoost 对混写拼写做硬错误检查，传 Boost_ROOT 即 FATAL，与值是否正确无关；libasd 实测只用全大写 BOOST_ROOT，从未设混写行 | 换路线做纠错而非加参：删除 generate() 内 `Boost_ROOT` 缓存行，仅保留全大写 `BOOST_ROOT` + `CMAKE_POLICY_DEFAULT_CMP0167=OLD`；原有 Boost_INCLUDE 三行与工具链修复、TMPDIR、测试开关均不动 |
| 11 | 拼写纠错后 configure 通过但 `cmake.build()` 仍死于 `boost/uuid/uuid.hpp file not found` (header.hpp:46)：FindBoost 未把头目录传给编译 | 上轮仅删混写行仍只依赖 FindBoost 输出变量（Boost_INCLUDE_DIRS/DIR/FOUND）；新日志证明 configure 过而编译缺头，说明 FindBoost 搜索未命中（输入提示缺失），输出缓存被覆盖或落空；libmatio 有同类模块模式下 -I/-L 兜底实测 | 换路线不再只调 FindBoost 变量：新增全大写输入提示 BOOST_INCLUDEDIR/BOOST_LIBRARYDIR，并经 CMAKE_C/CXX_FLAGS 注入 -I、经 LINKER_FLAGS 注入 -L（libmatio 同款），编译不再单点依赖 FindBoost 填充；BOOST_ROOT/CMP0167 与工具链修复保留 |
| 12 | 输入提示 + `cache_variables` 的 -I/-L 注入后仍在同位置失败（build line 174，uuid.hpp 缺失）：-D 缓存未到达编译器，或 Boost 顶层 includedirs 为空 | 上轮经 `tc.cache_variables` 传 CMAKE_CXX_FLAGS 被新日志证伪：行号推进仅因代码变长，编译错误纹丝不动；另怀疑 component 化 Boost 顶层 includedirs 为空或路径不存在，-I 指向空；libmatio 用的是 `tc.variables` 而非 cache | 换路线双保险落地：FLAGS 改走 `tc.variables`（libmatio 原样），include 解析加 `package_folder/include` 回退与存在性过滤加日志；并在已验证的 conan_toolchain.cmake 改写点直接 `string(APPEND CMAKE_CXX_FLAGS -I..)` + `link_directories(-L..)`，绕开 -D/工具链顺序问题 |
| 13 | 工具链 -I 追加已生效但编译仍死于同一 uuid.hpp 缺失 | 连续三轮只调 FindBoost 变量与 -I/-L 注入错误纹丝不动，证伪标志未送达假设；librevenge 实证 1.91.0 系 slim 构建缺头，libzmf/libwpd/libvisio 均 pin 1.90.0.3 保头完整；slim 包内根本无 uuid.hpp | 换依赖版本：requirements 切到 boost/1.90.0.3 全头版本；generate 回归 libkml 最小集并删除三处无效注入；编译器修复与 TMPDIR 保留 |
| 14 | Boost 修复后构建推进到本包编译：endian.hpp:97 报 needs to be set up for your CPU type | 上游头文件只认 x86/PPC/SPARC 与 Apple 系 arm64 宏，clang 在 aarch64-linux-ohos 下定义的 aarch64 宏不在任一分支；且 OHOS 非 glibc 使首分支被跳过 | 新增 0002 补丁：小端分支追加 aarch64/arm/ARMEL/M_ARM64，大端分支追加 ARMEB；只用标准编译器宏；conandata 注册 portability 补丁 |
| 15 | 字节序修复后构建推进：chipper.cpp 经 opt_allocator 报 boost/interprocess/file_mapping.hpp 缺失 | 1.90.0.3 系 CMake 按需裁剪头文件，十余个站内版本均无 interprocess；上游注释明示 interprocess/uuid 为必需头文件，核心另需 program_options/serialization/thread 编译库；1.90.0.4 为唯一全头加三库版本，仅缺核心未使用的 iostreams 库 | 换依赖到 boost/1.90.0.4，新增 0003 补丁从上游 REQUIRED 组件中去掉 iostreams；保留 0001/0002 与编译器修复 |
| 16 | 构建已推进到 ctest（Total Test time 0.07s）但标记失败：discovered=0/executed=0，LastTest.log missing（build/Release/Testing/Temporary/LastTest.log），伴随 preflight.sh 报 /tmp 只读 | 旧逻辑用 cmake.test() 且只在单一固定路径找 LastTest.log：CMakePresets 多配置布局下日志位置漂移或 0 测试时无日志即直接判失败且无 stdout 实证；TMPDIR 只经 conan Environment 透传，直接 subprocess 的 ctest 继承不到可写根 | 主配方 build() 改直调 ctest（cwd=build_folder，捕获 stdout，优先解析 % passed/out of 总结行，No tests 按失败闭环，LastTest.log 改递归多候选搜索），新增 _ensure_writable_tmp 把可写根钉进 os.environ（含可写探测与 .hmbs-tmp 回退）+ _ctest_binary（HMBS_CMAKE 同目录优先）；仅修证据链与临时根，不跳过任何测试 |
| 17 | ctest 已跑出 Total Test time 0.08s 且 exit=0，但标记仍 discovered=0/executed=0（LastTest.log missing）；stderr 另见 test/unit/point_test.cpp:8 上下文 | 旧 `_run_upstream_tests` 只在 `build_folder` 直跑 ctest（预设多配置下 CTestTestfile 可能漂移），总结行与单测行均用严格大小写/严格 `N/N Test #N` 前缀匹配，CMake 4.4 输出变体即漏检；失败 reason 不带目录清单与输出片段，无法定位 | 加固证据链（不跳过任何测试）：新增 `_locate_ctest_dir` 定位真实 CTestTestfile 目录并在此跑 ctest（显式透传 TMPDIR/TMP/TEMP）；总结行与单测行改大小写不敏感宽松匹配（`Test #N … Passed/Failed/Timeout/Skipped`，不再要求 `N/N` 前缀），输出同时记 head+tail；失败 reason 附目录清单/日志路径/exit/输出尾片段，LastTest.log 仍递归搜索；测试口径不变（仍为上游 `liblas_test` 单 ctest 用例） |
| 19 | ctest exit=0 且 TUT 输出 `tests summary: ok:80`、`Test Passed. "liblas_test"` 俱在，但标记仍 discovered=0/executed=0（LastTest.log missing） | 旧解析要求 `Test #N` 与 `Passed` 同一行 (`Test\s+#\d+.*Passed`)，而 ctest `--output-on-failure` 把头 (`1/1 Test #1: liblas_test`) 与 verdict (`Test Passed.` 独立行) 分两行打印，单行正则永不命中；`_find_last_test_log` 只搜 `build_folder` 未含已定位的 `ctest_dir`，ANSI 色码亦未剥离 | 主配方 `_run_upstream_tests` 只修证据链不跳过任何测试：ANSI 剥离；`LastTest.log` 搜索追加 `ctest_dir`；单行匹配保留并把 `.*` 收紧为 `[^\n]*`；新增分行头/尾关联计数 (头 `^\s*\d+/\d+\s+Test\s+#\d+` + 尾 `Test Passed/Failed/Skipped`)，有尾通过才认头数；TUT `tests summary: ok:N` 仅记日志不改 ctest 口径 |
| 18 | 真机 compile 阶段 Signal 9 无 stdout/stderr 日志中断 (discovered=0/executed=0) | 受限真机编译期 OOM killer 杀掉大 TU 编译进程 (Boost spirit/serialization/interprocess 模板膨胀 + Release -O3/调试信息峰值 RSS；与 pachi/12.9 无日志 Signal 9 同类) | 主配方低内存加固：conan_toolchain.cmake 末尾幂等追加 `string(APPEND CMAKE_C/CXX_FLAGS " -O1 -g0 -fno-rename-registers")` (Release -O3/-g 之后追加，后者生效) + _build_environment() 加法式 append CFLAGS/CXXFLAGS -O1 -g0；重型栈保持 OFF (GDAL/LASZIP/Utilities/GeoTIFF)，单作业沿用 HMBS jobs=1；不跳过任何测试 |
| 20 | test_package 在 CMakeDeps 生成阶段失败：`Component 'boost::boost_program_options' not found in 'boost'`（主包构建与上游 ctest 1/1 已通过） | 配方 package_info 误用 `boost::boost_*` 前缀组件名：经 GitCode API 只读核查站内 boost/1.90.0.4 的 package_info，其定义为 headers 聚合组件 `boost`（cmake Boost::boost）+ 标准组件 `program_options/serialization/thread`（cmake Boost::<name>），不存在 `boost_program_options` 等带前缀名，CMakeDeps 按名查找直接硬错误；cpp-rotor 前例不适用该版本 | package_info.requires 改为 `boost::boost` + `boost::program_options`/`boost::serialization`/`boost::thread` 标准名并修正注释；主包构建、补丁与测试口径不变 |
| 21 | test_package 的 ctest 在 0.03s 内失败（8 discovered / 0 passed），上游 `liblas_test` 1/1 仍通过；预检摘要截掉了 ctest 输出段，看不到具体哪个 CHECK 中断 | 直接证据只有 `test_liblas ***Failed 0.03 sec`：毫秒级失败且无断言输出，指向加载期中断而非断言失败——裸 `cmake.test()` 不继承聚合 runenv，若 boost 取到 shared 构建则消费者二进制在 loader 阶段即 abort；另 `add_test(COMMAND test_liblas)` 用裸名，在多配置/输出目录漂移时可能找不到二进制；TMPDIR 本身已由 `_build_environment()` 覆盖，与失败无直接因果（`[readonly_tmp]` 为通用启发式） | test_package 只修执行环境与证据链，不删不断言：① `test()` 内 ctest 改走 `self.run(ctest, cwd=build_folder, env="conanrun")`（TMPDIR 上下文内，runenv+可写临时根同时生效；ctest 路径优先 HMBS_CMAKE 同目录）；② 直接运行的可执行路径改为 `build_folder/bindirs/test_liblas` 显式锚定；③ CMakeLists 的 `add_test` 改用 `$<TARGET_FILE:test_liblas>`；④ 失败分支新增 `_dump_last_test_log()` 把 LastTest.log 头尾打进日志，下一轮可见真实中断行 |
| 22 | 上轮证据链生效，新日志给出精确失败行：`CHECK FAILED at line 47: header.GetDataFormatId() == liblas::ePointFormat0`（version/signature/version 行均已通过） | 测试对上游默认值的假设写错：经上游同 commit 源码核实，`Header::Header() : m_schema(ePointFormat3)`，默认点格式是 ePointFormat3 而非 ePointFormat0；`SetDataFormatId(PointFormatName)` 真实存在（header.cpp），可做 round-trip | 与上轮换策略（上轮修执行环境，本轮修错误期望）：test 第 2 组不断言删减、计数仍 8——先断言真实默认值 ePointFormat3，再 Set→Get round-trip 到 ePointFormat0 并恢复 ePointFormat3（下游 Point 组行为与默认一致）；仅改测试期望，不碰配方与补丁 |

## 源码修改
- `patches/0001-respect-build-shared-libs.patch`: `src/CMakeLists.txt`
  中 `add_library(las SHARED ...)` / `add_library(las_c SHARED ...)`
  改为无 `SHARED` 关键字版本, 使 `BUILD_SHARED_LIBS` 生效。无功能改动。
- `patches/0002-aarch64-endian-detection.patch`: `include/liblas/detail/endian.hpp`
  中小端分支追加 `__aarch64__/__arm__/__ARMEL__/_M_ARM64`, 大端分支追加
  `__ARMEB__`, 使 AArch64 OHOS 命中 `LIBLAS_LITTLE_ENDIAN`。无功能改动。
- `patches/0003-drop-iostreams-component.patch`: 顶层 `CMakeLists.txt` 的
  `find_package(Boost ... COMPONENTS ... REQUIRED)` 去掉 `iostreams`
  (核心 `src/` 与 `include/` 无 `iostreams::` 实际使用，仅已关闭的
  `apps/bigfile_boost_iostreams_test.cpp` 用过)。无功能改动。

## 依赖版本
- boost/1.90.0.4 (站内全头版本，b2 构建并且导出全部上游头文件，含 interprocess/uuid/spirit/multi_index；编译库 atomic/chrono/filesystem/program_options/regex/serialization/system/thread/timer；必需：program_options/serialization/thread 编译库 + 全套头文件)
- GeoTIFF 已关闭 (WITH_GEOTIFF=OFF)：libgeotiff/libtiff 不再依赖
  (上游 TIFF/JPEG/ZLIB 查找位于 WITH_GEOTIFF 块内，OFF 时干净跳过)

## 验证结果
- 待 HMBS 真机预检回填:
  - `conan create` 编译状态
  - 上游 `ctest liblas_test` 执行数/通过数 (以预检 stdout 为准)
  - test_package `test_liblas` 8 项断言执行情况

## 交付物
| 文件 | 说明 |
|------|------|
| archives/l/liblas/1.8.1.r145/conanfile.py | 主配方 (CMake) |
| archives/l/liblas/1.8.1.r145/conandata.yml | 源码 URL+sha256+补丁声明 |
| archives/l/liblas/1.8.1.r145/patches/0001-*.patch | 静态库开关补丁 |
| archives/l/liblas/1.8.1.r145/test_package/ | 消费者测试 (8 断言) + MANIFEST.yml |
| archives/l/liblas/1.8.1.r145/manifest.yaml | 版本级 manifest |
| archives/l/liblas/manifest.yaml | 软件级 manifest |

## 注意事项
- 上游测试为 TUT 框架, 非 gtest/pytest, 计数口径为 `liblas_test` 内
  `to::test<N>` 用例数, 需从预检 ctest 输出如实摘录, 不得估算。
- test_package 断言 `IsLibGeoTIFFEnabled()==false` 与配方
  `WITH_GEOTIFF=OFF` 绑定, 若后续重新打开该选项需同步修改测试
  (OFF 原因见问题表 #5：conancenter GeoTIFF 链在 OHOS 真机不可构建)。
- 本地未运行 conan (按任务守则, 真机验证由 HMBS 后台执行)。
