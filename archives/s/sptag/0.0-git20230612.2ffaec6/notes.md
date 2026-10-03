# sptag 0.0-git20230612.2ffaec6 适配笔记

## 编译环境
- 构建系统: cmake（上游 `CMakeLists.txt` + `AnnService/CMakeLists.txt`）
- 上游提交: `2ffaec67dd97dbb4f4bc5dda568a3f5ce6cab108`（2023-06-12，SECURITY.md 合并提交）
- 源码包: `https://github.com/microsoft/SPTAG/archive/2ffaec6....tar.gz`（1.39MB，sha256 见 conandata.yml）
- 编译日期: 2026-10-01（首轮：配方与补丁已完成，待 HMBS 真机预检）
- 编译器: clang 15（OHOS aarch64，`compiler.cppstd=17`，Release）
- 状态: built（配方完整；真机验证通过前不标 published）

## 编译步骤

用文字描述实际编译步骤（首轮为设计态，真机实测后回填耗时与日志证据）：

1. `source()`：解 SPTAG 源码包；`ThirdParty/zstd` 是 git submodule（tarball 里是空目录），接着 vendor zstd 1.5.5 release 包进去，上游 `add_subdirectory(ThirdParty/zstd/build/cmake)` 即可照常工作。
2. `generate()`：CMakeToolchain 注入 `GPU=OFF`、`SPTAG_BOOST_INCLUDE_DIR/LIBRARIES`（boost1.84 全量头 + 5 个静态库绝对路径）、SDK OpenMP（-fopenmp，无 conan 包）、`CMAKE_DISABLE_FIND_PACKAGE_{Python3,Python2,JNI,MPI,CUDA}=TRUE`；OHOS 下追加 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`。
3. `build()`：打 7 个补丁 → `cmake.configure()` → `cmake.build()`（SPTAGLib/SPTAGLibStatic、server/client/aggregator/indexbuilder/indexsearcher/quantizer/ssdserving、SPTAGTest）→ 直接运行 `Release/SPTAGTest --log_level=test_suite`（上游 154 个 Boost.Test 用例，无 ctest 注册）。
4. `package()`：`cmake.install()`（lib/ + bin/）+ 把 `AnnService/inc` 按上游 `inc/...` 布局装到 `include/inc`（与 SPTAG.nuspec 的消费布局一致）；`shared=False` 时删 `lib/*.so*`。
5. `test_package`：CMakeDeps 消费 `sptag::sptag`，编译运行 `test_sptag`（KDT/BKT 建索引/存取/搜索 top-1 自查，12 个断言）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 顶层 CMake `FATAL_ERROR "Unrecognized compiler"` | 只接受 GCC/MSVC；OHOS 用 Clang | 0001：Clang 走 GNU 分支（`-fopenmp -lm -lrt -std=c++14` 在 OHOS clang 可用，待真机证实） |
| 2 | Conan 工具链 flags 被上游 `set(CMAKE_CXX_FLAGS ...)` 覆盖 | 上游覆盖而非追加，`conan_toolchain` 的 INIT 值丢失 | 0001：改成 `"${CMAKE_CXX_FLAGS} ..."` 追加（含 RELEASE 变量） |
| 3 | 上游 `find_package(Boost ...)` 在 OHOS 找不到包 | OHOS 无系统 Boost；制品仓是 boost1.84 组件包（无 BoostConfig） | 0001/0007：配方拼绝对路径 `SPTAG_BOOST_INCLUDE_DIR/LIBRARIES`，CMake 里 Conan 分支优先、系统查找保留为 fallback |
| 4 | `-mavx2 -mavx512f...` 在 aarch64 上非法 | `AnnService/CMakeLists` 按编译器（GNU）而非架构加旗 | 0002：仅 x86 目标加这些旗 |
| 5 | `<cpuid.h>/<xmmintrin.h>/<immintrin.h>` 在 ARM 不存在 | `InstructionUtils.h` 无条件包含 | 0004：非 x86 给 `cpuid()` 内联桩（全 0 → 检测逻辑自然全 false，走标量路径） |
| 6 | `SIMDUtils.cpp`/`DistanceUtils.cpp` 全是 SSE/AVX/AVX512 内建函数 | SPTAG 用 SIMD 加速求和/距离 | 0005/0006：非 x86 下每个 SIMD 入口转发到头文件里的标量模板（与 x86 标量尾巴逐行一致）；`DistanceTest` 会数值验证 |
| 7 | `_mm_malloc/_mm_prefetch/ACCESSPERMS` 可移植性 | `Common.h` 假设 x86；musl 未必有 ACCESSPERMS | 0003：C++17 分支本来就不用 `_mm_malloc`；补 pre-C++17 的 ARM 分支、`__builtin_prefetch` 回退、`ACCESSPERMS` 兜底 |
| 8 | `unit_test_framework` 在 OHOS 无编译库 | `boost1.84-*` 只产出 thread/serialization 等；`boost/1.90.0` 的 test 库版本混杂风险 | 0007：测链改 header-only（`included/unit_test.hpp`），与 luacxx/ismrmrd/tsl-sparse-map 同方案 |
| 9 | `find_package(OpenMP)` 硬 FATAL | OHOS musl 无系统 OpenMP 运行时（b2sum/jpegqs 均禁 OpenMP） | recipe 改用 OHOS SDK 自带 OpenMP（clang -fopenmp 自动链接 SDK libomp，无 conan 依赖） |
| 10 | `SPTAGTest` 被 install 到 `bin/` | 上游行为，测试二进制不应进交付包 | 0007：删掉该 install 规则（server 等工具保留，配 commands.json） |
| 11 | Wrappers（Python/Java/C#）configure 期调 swig | 真机无 swig/JDK/dotnet，`execute_process` 行为不可控 | `CMAKE_DISABLE_FIND_PACKAGE_*` 确定性关闭；库+工具+测试不受影响 |
| 12 | `VectorIndex.cpp:926` 在 OHOS clang 报 `-Wnon-pod-varargs` 硬错误 | `SPTAGLIB_LOG`（C 变参 `Logging(..., const char*, ...)`）被传入 `std::string`（UB，clang 提示运行时 abort）；同文件/同树其余 3 处同类调用均已 `.c_str()`，仅此一处上游遗漏 | 配方 `build()` 内 `replace_in_file` 补 `.c_str()`（未走 `patches/`：该文件为 CRLF 换行，与 `gen_patches.py` 的 LF-only 约束冲突；单行锚点不含换行符，两种换行均可命中；未命中则直接抛错） |
| 13 | `AsyncFileReader.cpp:45` 报 `use of undeclared identifier 'pthread_setaffinity_np'`（真机 preflight compile 失败） | OHOS musl 无 glibc 扩展 `pthread_setaffinity_np`（knowledge E211）；`SetThreadAffinity` 仅被“线程自身”调用（`ListionIOCP` 内、`IndexSearcher/main.cpp` 与 `SSDIndex.h` 的 search 线程，均对自身 `threads[i]` 设亲和性），故 `sched_setaffinity(0, ...)` 语义等价 | 配方 `build()` 内 `replace_in_file`：`__OHOS__`/`!__GLIBC__` 分支改用 `sched_setaffinity(0, ...)` 并补 `#include <sched.h>`；glibc 分支保持原样。曾用 `patches/0008` 实现，但 conan 打补丁器无偏移搜索、因 hunk 行号失败，改用行号无关的 `replace_in_file`（与 #12 同模式） |
| 14 | 真机 `SPTAGTest` 首个 BuildSSD 用例失败：`Failed to create file handle: zbtest/ssd_Float_L2_BKT_DEFAULT.ssd_index` → `Cannot Load SSDIndex!` → `Failed to build index.`（76/77 通过，中断后 77 个未起跑） | 非目录缺失：写路径（SimpleFileIO）已成功、`BuildIndex` 返回 true；失败点是 `LoadIndex` 经 `AsyncFileIO::Initialize` 以 `O_RDONLY\|O_DIRECT` 打开刚写好的同一文件。真机预检文件系统拒绝 `O_DIRECT`；且 HongMeng 内核可能无 Linux AIO（`io_setup` 系列），`Initialize` 直接返回 false。属 OHOS 文件系统/内核能力差异，非测试逻辑错误 | 配方 `build()` 内 `replace_in_file`（与 #12/#13 同模式，不占补丁编号）：`O_DIRECT` 失败时回退普通 `open`；`io_setup` 失败时销毁已建 context、清空 `m_iocps` 并以同步 `pread` 模式继续（`ReadFileAsync`/`BatchReadFileAsync` 同步回退，`HasAio()` 判定，不起 IOCP 线程）；`ShutDown` 加哨兵守卫。快速路径优先、仅失败时回退，测试断言零改动。另把测试 `cwd` 显式固定为 `build_folder`，`zbtest`/`sddtest` 在 `build_folder` 与测试二进制所在目录双建并打印诊断行 |
| 15 | 真机 `SPTAGTest` 运行瞬间断连：`RUN: .../Release/SPTAGTest --log_level=test_suite > .../sptagtest.log 2>&1` 后 `Connection to 47.242.172.160 closed by remote host`，编译链接已 100% 通过（`Built target SPTAGTest`），零测试证据 | 双因：① `O_DIRECT` 回退到普通 `open` 后仍走 `io_setup`/`io_submit` AIO 路径（`HasAio()` 为 true），而 Linux 内核 AIO（`IOCB_CMD_PREAD`）要求 `O_DIRECT`，普通 fd 上 `io_submit` 永不成功 → `BatchReadFileAsync` 内 `submitted/totalDone` 永不推进、无限自旋，SSH 空闲至远端主动断开；② 全量 154 用例单次静默 `self.run`（输出重定向、无心跳），重用例（SSDServing 121 个 1000x100 建索引、PerfTest 2000x128 穷举真值 + `Sleep(10000)`x2）使空闲窗口长达数分钟 | ① `Initialize` 记 `_hmbsDirect`：`O_DIRECT` 失败回退普通 `open` 成功时直接 `m_iocps.clear(); return true`（同步 `pread` 模式，不调 `io_setup`），AIO 路径只走真正的 `O_DIRECT` fd；② `build()` 内上游测试改为 12 套件逐个 `self.run --run_test=<suite>`（轻套件先、Perf/SSDServing 后），每套件独立日志 + 起止诊断行保活，计数为各套件 `Running N` 头之和与 `Entering/Leaving test case` 分段聚合（恒等式不变），测试断言零改动 |
| 16 | 真机计数校验失败 `executed=153 passed=153 discovered=150`（Base64 套件 Error 200，另 3 个单用例套件 discovered 为 0） | 双因：① 配方用文件名 `Base64HelperTest` 做 `--run_test` 过滤，但上游套件实为 `BOOST_AUTO_TEST_SUITE(Base64Test)`，零匹配退出 200 少计 1 个；② discovered 正则只匹配复数 `test cases`，漏掉 IniReader/Filter/SIMD 的单数 `Running 1 test case` 头，共少计 4 个 | `_suites` 首项改为 `Base64Test` 并加注；两处 `Running` 正则改为 `test cases?` 单源兼容单复数；`MANIFEST.yml` 对应命令同步修正。复跑后上游 154/154 通过 |
| 17 | test_package 配置失败 `Library 'zstd_static' not found in package` | zstd CMake 目标名（libzstd_static）与产物名（OUTPUT_NAME=zstd，即 libzstd.a/.so）不一致，`cpp_info.libs` 误用了目标名；另 `DistanceUtils` 为静态辅助归档、上游无 install 规则，静态消费方会缺 SIMD 符号 | `package_info` 改用真实库 stem `zstd`；`package()` 从源码/构建树拷贝 `libDistanceUtils.a` 进包，静态 `libs` 增为 `SPTAGLibStatic/DistanceUtils/zstd` 依赖序 |
| 18 | `package()` 内 DistanceUtils 拷贝报 `cannot access local variable 'shutil'`，包内仍无该归档，test_package 报 `Library 'DistanceUtils' not found` | 方法内后段冗余的 `import shutil` 使 `shutil` 成为函数级局部变量，前段拷贝代码执行时该局部变量尚未绑定（UnboundLocalError），文件本身存在但拷贝从未成功 | 删除方法内冗余 `import shutil`（文件顶部已有全局导入），保留原拷贝逻辑不变 |
| 19 | test_package configure fail: sptag-Target references boost1.84::boost1.84 but target not found (wserialization BoostConfig won overwrite) | sptag package_info used implicit aggregate target while all boost1.84-* set cmake_file_name=Boost, files overwrite, winner lacks filesystem target; plus redundant serialization pkg | requirements drop boost1.84-serialization (wserialization already ships both libs), package_info explicit component requires, test_package CMakeDeps rename thread/wserialization file names (cpp-hocon precedent) |
| 20 | test_package `RUN: "./test_sptag" > log 2>&1` 报 `Error 127`（主包编译+上游 154/154 已通过） | 相对路径+错误 cwd：`bindirs[0]` 在 cmake_layout 下为 `.`，`./test_sptag` 仅当 cwd=build dir 才可解析，而 `test()` 默认 cwd 并非 build dir；真机日志 `RUN: "./test_sptag"` 即证据。主包 `SPTAGTest` 用绝对路径直跑成功，反证非二进制损坏/签名问题。另默认 `/bin/sh` (mksh) 在 OHOS 上不可靠（zlib/模板先例须用 bash 包装） | `test()` 改绝对路径+存在性校验+递归回退（找不到则列 build dir 前 30 项 loudly 失败，不再裸 127）；`_resolve_shell` 取 `CONFIG_SHELL`/which/`/data/service/hnp/bin/bash`；`self.run(bash -c 'abs_bin > abs_log 2>&1', cwd=bin_dir)`；`build()` 增 `glob test_sptag*` 诊断行 |

## 源码修改

7 个补丁（`patches/`，均已用 `git apply --check` 对 pristine 源码校验通过）：

| 补丁 | 内容 |
|------|------|
| 0001 | 顶层 CMake：Clang 分支、flags 追加、Conan Boost 注入 |
| 0002 | AnnService：SIMD 编译旗仅 x86 |
| 0003 | Common.h：可移植分配/prefetch/ACCESSPERMS |
| 0004 | InstructionUtils.h/.cpp：非 x86 cpuid 桩 |
| 0005 | SIMDUtils.cpp：12 个求和核标量转发 |
| 0006 | DistanceUtils.cpp：24 个距离核标量转发 |
| 0007 | Test/CMakeLists + main.cpp：header-only Boost.Test、不安装测试二进制 |

线程亲和性（musl/OHOS `sched_setaffinity`）为配方 `build()` 内 `replace_in_file`（见上表 #13），不占补丁编号。

补丁均使用上游/标准架构宏（`__x86_64__` 等）做平台判断，未引入 `__OHOS__` 平台宏。

## 依赖版本

本次编译依赖的具体软件版本（以真机 conan 图为准，首轮为配方声明值）：

- boost1.84/1.84.0（全量头 + filesystem/regex 静态库）
- boost1.84-thread/1.84.0（libboost_thread.a，chrono 自包含）
- ~~boost1.84-serialization/1.84.0 (removed: redundant, wserialization already ships libboost_serialization.a)~~（libboost_serialization.a）
- boost1.84-wserialization/1.84.0（libboost_wserialization.a）
- OpenMP 由 OHOS SDK clang 提供（-fopenmp 自动链接 SDK libomp，无 conan 包依赖）
- zlib/1.3.1.2（override：boost1.84 传递依赖 conancenter zlib/1.3.1，其 CMake 构建不识别
  HarmonyOS 平台（"System is unknown to cmake"）且与共享 profile 陈旧编译器路径耦合；
  本仓 1.3.1.2 同源（同为 1.3.1 tarball）但用 ./configure+make，绕过 CMake 平台检查；
  sptag 以 override=True 强制全图使用该 OHOS 已验证配方）

说明：`system` 自 Boost 1.69 起 header-only，无需链接；`unit_test_framework` 只用于 SPTAGTest，已被 header-only 方案替代，故不依赖。

## 验证结果

首轮（工作树未提交，无真机数据）：
```bash
# 待 HMBS 真机预检执行：
#   conan create archives/s/sptag/0.0-git20230612.2ffaec6 -pr:h=ci/conan/profiles/ohos-aarch64 ...
# 预期证据：
#   - Release/SPTAGTest --log_level=test_suite：154/154 通过
#   - test_sptag：12/12 断言通过
```

上游测试盘点（已审计源码，非猜测）：`Test/src/*.cpp` 共 12 个 suite、39 个 `BOOST_*TEST_CASE`（main.cpp 为 runner；`make_gist_sptag.py` 为数据脚本；`WinRTTest` 仅 Windows）。测试全部自包含（运行时生成合成向量，无网络/外部数据集）。

第二轮（真机预检：下载已通，`SPTAGTest` 退出码 1 但旧配方直接抛错、无任何用例计数）：`conandata.yml`
主源码/zstd 均已加 `gh-proxy.com` 镜像回退（官方 URL 保留最后，sha256 不变），下载问题解决、编译链接通过。
`build()` 改为失败证据 surfacing：捕获非零退出后仍解析 `sptagtest.log`（Entering/Leaving test
case 分段，`error in` 判失败，起跑未完成计崩溃失败），输出 `SPTAGLOG |` 尾部 80 行并带真实计数的
`HMBS_UPSTREAM_TEST_RESULT`（含 `gaps`），之后重新抛错保持失败态；下一轮按真实失败用例定位根因。

## 交付物

真机验证通过后再填（conan 包名 `sptag/0.0-git20230612.2ffaec6`，含 `libSPTAGLibStatic.a + libzstd_static.a`、`include/inc/**`、`bin/{server,client,aggregator,indexbuilder,indexsearcher,quantizer,ssdserving}`）。

## 注意事项

- `LIBRARYONLY` 保持 OFF：工具与 SPTAGTest 都要编；`bin/` 有产物故配了软件级 `commands.json`（scrappie 先例）。
- `-march=native`（上游 Release flags）在 aarch64 clang 合法，原生构建故保留；若 CI 机型混杂导致非法指令问题，后续轮次再按架构限定。
- `-lrt` 保留（musl 一般自带 stub）；若 OHOS SDK 无该 stub，真机链接报错时去掉。
- `testidx_kdt`/`testindices` 等是测试运行期在构建目录生成的数据目录，不进包。
- 真机若报二进制 `Operation not permitted`（部分 OHOS 分区要求自签名），参考 sassc/scalapack 先例在运行前加 `binary-sign-tool sign -selfSign 1`；`scrappie` 同类直跑方案在 CI 可用，故首轮不预置。
| 21 | compile fail SearchService.cpp via boost yield_k well sp_thread_sleep undeclared pthread_setcancelstate x2 | OHOS musl lacks cancel API, boost1.84 header only excludes ANDROID, old macro never checked | generate writes sptag_ohos_pthread_stub.h to build folder and force-includes via -include for all TUs, c10t precedent |
| 22 | 同指纹第2次失败：带generate垫片复跑仍报sp_thread_sleep两处pthread_setcancelstate未声明（构建行号+57证明垫片已参跑） | 工具链INIT旗标未必 survive 上游旗标处理，或__linux__门控为假；属通道问题非语义问题 | 改主通道为CMake级：build()写源码树ohos_pthread_compat.h并经add_compile_options目录作用域-include（set覆盖免疫，行号无关replace_in_file）；门控放宽为__OHOS__或非glibc；两通道同守卫同内容可共存；test_package同样加垫片（放tc.generate前） |
| 23 | 同指纹第3次失败：compile 在 `huf_decompress_amd64.S.obj` 崩（alltypes.h/pthread.h/ohos_pthread_compat.h 全报 unexpected token / unrecognized instruction mnemonic，Error 1 中断） | 上一轮“通道太窄”假设反了：垫片已参跑且过宽。zstd 1.5.5 CMake 把该 .S 强制为 LANGUAGE C（aarch64 上靠 ZSTD_ENABLE_ASM_X86_64_BMI2 置空，本可正常编过）；目录级 `add_compile_options("-include ...")` 与 `extra_cflags -include` 都不分语言，把 C 头强塞进该 ASM TU 预处理，汇编器逐行报错 | 改窄不改宽：CMake 通道加 COMPILE_LANGUAGE 生成器表达式（C/CXX 才 -include，ASM 不受影响）；generate() 备用垫片只进 extra_cxxflags（Boost C++ TU 才需要，zstd 纯 C/ASM 不再被污染）；zstd ASM 本体不动（上游宏已处理 aarch64） |
| 24 | 同指纹第4次失败：COMPILE_LANGUAGE 收窄后原样复现（同 .S 同头同行号类错误，build()+11 行证明新代码已参跑） | genex 按语言过滤，但 zstd 把该 .S 强制为 LANGUAGE C，`COMPILE_LANGUAGE:C` 仍命中——错不在表达式而在注入位置：顶层目录作用域天然覆盖先 add 的 zstd 子目录 | 换路线为作用域移位：注入点从顶层前部改到 `add_subdirectory(ThirdParty/zstd/build/cmake)` 之后（目录作用域只覆盖后加的子目录，zstd 彻底看不见 -include；AnnService/Test 照常覆盖）；genex 与 CXX-only 备用垫片保留做纵深 |
| 25 | test_package `test_sptag` 启动即 127：`Error loading shared library libomp.so` + `__kmpc_*`/`omp_*` 未定义重定位（主包编译链接 100% 通过；stat 750/access X=True；绝对路径+shell 重定向仍 127） | 非 cwd/执行封装问题：`-fopenmp` 链接的 libomp.so 在 SDK 工具链目录（`<bindir>/../lib/aarch64-linux-ohos`），不在 loader 默认路径；此前三轮只改执行封装（相对路径→绝对路径→shell 重定向）未补运行时库路径，故同指纹复现 | 新路线（faiss/1.15.0 先例）：`_sdk_omp_libdirs()` 从 live 编译器路径推导含 libomp.so 的目录；`build()` 内导出到 `LD_LIBRARY_PATH`（自包 runenv 对自身 build() 不可见）；`package_info()` 经 `runenv_info` 暴露 `LD_LIBRARY_PATH` 给 test_package 的 conanrun；系统链接保持 `-lomp` 不变 |
| 26 | 同指纹第2次失败：`LD_LIBRARY_PATH` 双通道（build 内导出 + package_info runenv）后 test_package 仍报完全相同的 libomp.so 缺失 | 主包 SPTAGTest 在同一预检、同一真机上可运行（能走到 test_package 即证明 12 套件已跑完），唯消费者二进制失败——差异必在二进制自身链接形态而非全局环境：SPTAG 可执行文件经 clang 驱动以绝对路径链接 libomp，消费者经 `-lomp`（system_libs）只记裸 soname；runenv 未到达该运行上下文，故纯环境方案按构造就不充分 | 换路线为链接期嵌入：test_package/CMakeLists 新增 `SPTAG_OMP_RPATH` → `LINKER:-rpath`；test conanfile 自包含同源发现逻辑并在 `tc.generate()` 前注入该变量（同机链接同机运行，无跨机陈旧问题）；主包 runenv/build 导出保留为纵深，不再动执行封装 |
| 27 | 同指纹第3次失败：消费者 RUNPATH 嵌入后仍完全相同（行号 274→352 证明上轮改动确已同步参跑，故非同步问题；报错逐字相同） | 前两轮的目录都从“编译器所在位置相对推导”（harmonybrew/migrated 布局），而仓库自带 profile（`ci/conan/profiles/ohos-aarch64` 的 `[buildenv] LD_LIBRARY_PATH`）与 E120/E132/fblocks 草稿一致 pin 定权威 SDK 目录 `.../ohos-sdk_*/ohos/native/llvm/lib`（llvm/lib 下有 libomp.so）；编译器相对路径猜错即静默返回空，runenv/rpath 全成空操作。另 conanrun 聚合语义不明，环境变量未必到达子进程 | 新路线（与 R2/R3 的编译器相对推导完全不同）：版本通配的权威 SDK 绝对路径（存在且含 libomp.so 才用）置于最高优先级；test() 内双保险——`os.environ` 导出 + 命令串首 `LD_LIBRARY_PATH="..."` shell 前缀（子 shell 必继承，不依赖 conan 聚合语义）；失败时把 omp_dirs/进程 LD/NEEDED libomp/RUNPATH/目录清单拼进异常消息（stderr 尾部必现，不再依赖易截断的中段日志）；主包 build()/package_info() 同源补齐 |
| 28 | 真机 compile 在 AnnService 模板 TU 中段 SSH 断开（BKTIndex/IQuantizer/KDTree 仅 warning 无 error，jobs=1 且工具链尾部 -O1 -g0 已参跑仍断） | 工具链文件在 project() 前被包含，上游顶层 set(CMAKE_CXX_FLAGS_RELEASE ... -O3 -march=native) 在其后追加，命令行上 -O3 落在 -O1 之后（last -O wins），降优实际未生效；-march=native 另增 ARM 代码生成负担 | build() 内对源码 CMakeLists 做 replace_in_file：-O3 改 -O1、去 -march=native、加 -g0（锚点行号无关，缺失则大声失败）；工具链尾部保留做纵深，断言与测试口径不动 |
| 29 | test_package 第4次同指纹失败：RUNPATH 嵌入后仍逐字相同 `libomp.so + __kmpc_*/omp_*` 未定义 → Error 127，且本轮证据 `omp_dirs=NONE`（SDK 通配 glob 与编译器相对推导双双落空；真机 clang 在 `~/.harmonybrew/bin/clang`，其相对 `../lib*` 无 libomp.so；`procLD` 亦无 SDK llvm/lib，runenv 未到达该运行上下文） | 三轮环境/RPATH 路线按构造就不充分：凡需“猜目录”在 harmonybrew 布局下皆可静默为空，且纯环境方案依赖 conan 聚合语义。根治应消灭运行时依赖而非继续猜路径 | 换路线为主静态链接+发现加固：① build() 内对源码 CMakeLists 做 replace_in_file，Clang-only 追加 `-static-openmp` 到 CXX/EXE/SHARED 链接旗（GCC 开发构建不受影响；`find_package(OpenMP)` 的 `-fopenmp` 保留，static 优先）；test_package/CMakeLists 同源追加 compile+link options；RPATH/LD 双通道保留为纵深。② 发现逻辑加固（两 conanfile 同源）：SDK 精确 pin 版优先+通配、工具链 prefix 派生（llvm/lib 等）、编译器直查（`-print-search-dirs`/`-print-resource-dir` 解析含 libomp.so 的目录）、进程既有 LD_LIBRARY_PATH 复用。测试断言与计数口径零改动 |
