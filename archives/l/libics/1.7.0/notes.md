# libics 1.7.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: clang/clang++
- 状态: built（待 HMBS 真机预检）
- 申请人: liucu
- 队伍: 龙骑士

## 上游测试审计
- 上游仓库: https://github.com/svi-opensource/libics（tag 1.7.0）
- 构建系统: CMake（CMakeLists.txt）与 Autotools（Makefile.am/configure.ac）双轨，本配方选用 CMake
- 上游测试来源:
  - CMakeLists.txt：10 个 TEST_PROGRAMS（test_ics1/test_ics2a/test_ics2b/test_compress/test_gzip/test_strides/test_strides2/test_strides3/test_metadata/test_history，zlib 启用时含 test_gzip），注册为 13 个真实 ctest 用例 + 1 个 ctest_build_test_code 构建辅助项；support/cpp_interface/CMakeLists.txt 再加 4 个 TEST_PROGRAMS（test_ics2a_cpp/test_ics2b_cpp/test_metadata_cpp/test_history_cpp），注册为 7 个真实 ctest 用例；合计 20 个真实测试
  - Makefile.am：check_PROGRAMS 10 个，TESTS 8-11 个 shell 包装（TESTS1 8 个 + zlib 时 TESTS2 2 个 + gz 扩展时 TESTS3 1 个）
- 依赖: zlib（README 明确推荐安装，CMakeLists 以 find_package(ZLIB) 接入，Autotools 以 --with-zlib-include-dir/--with-zlib-lib-dir 接入）
- 1.7.0 变更: 新增 Ics_real16 半浮点支持、_Float16 编译器探测、Aurox 显微镜类型

## 编译步骤
- `get()` 下载 tag 1.7.0 归档并校验 sha256
- `generate()` 生成 CMakeToolchain（BUILD_SHARED_LIBS=OFF、LIBICS_USE_ZLIB=ON、CMAKE_POLICY_VERSION_MINIMUM=3.5）与 CMakeDeps；zlib 头文件与静态库路径从 Conan 依赖显式注入（ZLIB_INCLUDE_DIR/ZLIB_LIBRARY）
- `cmake.configure()` + `cmake.build()` 编译 libics
- `build()` 内运行 `ctest --output-on-failure` 执行全部 20 个上游真实测试，解析输出并打印 HMBS_UPSTREAM_TEST_RESULT 机器证据行；任一失败即抛异常使构建失败
- `cmake.install()` 安装库与头文件；构建证据 hmbs_upstream.json 随包持久化到 res/，供 test_package 在缓存命中轮次重放
- test_package 以 CMake 构建 test.c（调用 IcsGetLibVersion/IcsOpen/IcsSetLayout/IcsSetData/IcsSetCompression/IcsAddHistoryString/IcsClose/IcsGetLayout/IcsGetData/IcsGetHistoryString），运行后统计 5 个 CHECK-OK 检查点并打印 HMBS_TEST_PACKAGE_RESULT

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游库文件名与 Conan 包名不一致 | CMakeLists 设 OUTPUT_NAME 为 ics，产物为 libics.a | package_info 声明 cpp_info.libs 为 ics，并设置 cmake_file_name 与 cmake_target_name |
| 2 | find_package(ZLIB) 可能命中系统 zlib | 模块模式不走 Conan config 包 | 按 curl 配方先例显式注入 ZLIB_INCLUDE_DIR/ZLIB_LIBRARY，同时生成 CMakeDeps |
| 3 | 上游测试二进制为 EXCLUDE_FROM_ALL | 直接 ctest 找不到测试程序 | ctest 首项 ctest_build_test_code 自动构建全部测试目标后再执行 |
| 4 | 真机 cmake 报 System is unknown / 编译器检查失败 | CMakeToolchain 把 OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS，CMake 4.x 无该平台模块 | generate()（主配方与 test_package）在 OHOS 下强制 CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64，工具链仍为 OHOS clang（E092：julius/itsy_bitsy/oystr/zxc/byte-lite 同款）；同时修正 ZLIB 路径为 package_folder 绝对路径并在 build() 前确保 TMPDIR 可写 |
| 5 | 上轮 cache 变量平台覆盖已上机（失败行号 72→91）但 C/CXX identification unknown 复现；本轮原因含“源码下载失败” | cache 强写平台名与 Conan 自身 HarmonyOS sysroot/target 注入不在同一层，且 conf  pin 的 /data/service/hnp/bin/clang(++) 在部分 worker 不可用；下载行实为一次超时后重试成功（Sources correctly downloaded），且 .gitcode/review-memory.md 明确镜像 fallback 由 CI 自动加、conandata 只写官方 URL | 换减法+守卫路线（libwmime 第 16 轮同指纹收敛结论）：平台别名改 plain tc.variables 单变量 Linux（去 PROCESSOR/STATIC/WORKS 旁路，保留真实编译器检查）；主从配方新增 conf 编译器可用性守卫（悬空时 pin PATH 解析的 clang/clang++）；conandata 保持官方 URL 不动；ZLIB 绝对路径与 TMPDIR 硬化保留 |
| 6 | 识别期通过、主库编至 86%，C++ 接口 libics.cpp.o 报 no member named Real16（93% 处，GetLayout/SetLayout 两处） | 上游 tag 1.7.0 缺陷：C 库新增 Ics_real16 但 C++ 头 support/cpp_interface/libics.hpp 的 ics::DataType 枚举未同步（同目录 libics.cpp 已用 Real16）；上游 master 已补回该枚举项，与平台无关 | 新增 portability 补丁 0001（与 master 逐字一致的一行枚举项），conandata/manifest 登记；上游测试计数 13→20（C++ 接口 7 个：ics2a/2b/metadata1-4/history_cpp），MANIFEST 补登记；不关闭任何测试 |
| 8 | ctest_build_test_code Failed, 21 个测试 0 通过, `test_history_cpp` 链接报 `undefined symbol: crc32/deflateInit2_/deflate/inflate...` (libics_gzip.c.o in libics.a) | 上游 `target_link_libraries(libics PUBLIC ${ZLIB_LIBRARIES})` 仅在 FindZLIB MODULE 模式有效;CMakeDeps 提供 CONFIG 包时 ZLIB_FOUND 为真但 legacy 变量为空,配方又强制 LIBICS_USE_ZLIB=ON,导致带 -DICS_ZLIB 编译却无 zlib 链接,静态库可建但全部测试可执行文件链接失败 | conanfile 新增幂等 `_patch_zlib_link()`(source/build 双入口):保留上游 MODULE 行,追加 `if(TARGET ZLIB::ZLIB) target_link_libraries(libics PUBLIC ZLIB::ZLIB)` 守卫(PUBLIC 传递给全部 C/C++ 测试);package_info 追加 `requires=["zlib::zlib"]` 供消费者静态链接;不删测试 |
| 7 | 上轮补丁 0001 真机 apply 失败：`Failed to apply patch ... source file is different - support/cpp_interface/libics.hpp`（conan 指出来源行与补丁上下文不一致，首个失配处实际为 `UInt32, // integer, unsigned, 32 bpp`） | 补丁文件的 hunk 头（行号 80）与空格上下文与归档源码逐字节不一致，conan 做严格校验直接拒绝；根因假设（缺 Real16 枚举）正确，但补丁载体不可靠 | 换路线：删除 patches/0001 与 conandata patches 登记，改由 conanfile.py 内 `_fix_cpp_real16()` 在 source()/build() 双入口程序化补齐（SInt64→Real32 边界锚点、复用文件自身缩进与换行、已存在则 no-op、锚点缺失则 loudly 失败；插入行与上游 master 完全一致）；conandata 注释说明无补丁原因，manifest patches_applied 置空；本地以 tag 原文枚举块验证插入顺序、幂等与 CRLF 兼容 |

| 9 | CI #48874（CI-020）ctest_build_test_code 在链接 test_gzip 时 lld 启动崩溃，21 项全失败，但主库 libics.a/libics_cpp.a 均 100% 编译成功 | OHOS SDK 的 lld 动态链接 libxml2.so.16，CI worker 沙箱默认库搜索路径解析不到兼容版本（E266；babeltrace DRAFT-6048 及已合入 julius-1.8.0 同指纹）。非配方链接缺库：崩溃发生在 lld 启动期，早于读取任何输入库 | 主配方与 test_package 的 build() 新增 _ensure_lld_runnable()：经 clang -print-resource-dir 动态推导 SDK llvm/lib（含 libxml2.so.16 才注入），前置到 LD_LIBRARY_PATH（configure/build/ctest 子进程均继承）；无硬编码绝对路径，推导失败优雅降级；不切换链接器（GNU ld 产物在 OHOS 沙箱不可执行）、不删测试 |

## 源码修改
配方内 `_fix_cpp_real16()`（conanfile.py，source() 与 build() 双入口调用，幂等）：上游 tag 1.7.0 的 C++ 接口头文件 `support/cpp_interface/libics.hpp` 的 `ics::DataType` 枚举遗漏 `Real16`，而同目录 `libics.cpp` 的 GetLayout/SetLayout 已使用 `DataType::Real16`（C 库 1.7.0 新增 `Ics_real16`，C++ 头未同步），致 `libics_cpp` 在 93% 处编译失败；函数以 SInt64→Real32 边界为锚点插入与上游 master 完全一致的 `Real16, // real, signed, 16 bpp` 一行（复用文件自身缩进与换行，已存在则 no-op，锚点缺失则抛异常）。上一轮曾用 patches/0001 补丁文件实现同一修复，真机 `apply_conandata_patches` 因上下文逐字节失配被拒（`source file is different`），本轮已删除该补丁文件并取消 conandata 登记，改用此程序化路线。

## 依赖版本
- zlib/1.3.1（Conan 制品仓已发布版本）

## 验证结果
待 HMBS 真机预检回填（conan create 全量日志为准）：
- 上游 ctest 执行数/通过数：待回填
- test_package 5 项检查：待回填
- 证伪检查（参照文件非空、失败桩确认 harness 有效、区分通过与静默跳过）：随预检执行

## 交付物
| 文件 | 说明 |
|------|------|
| archives/l/libics/1.7.0/conanfile.py | CMake 配方（含上游 ctest 与证据标记） |
| archives/l/libics/1.7.0/conandata.yml | 官方 tag 源码 URL + sha256 |
| archives/l/libics/1.7.0/test_package/ | 消费者测试（test.c + CMakeLists + conanfile + MANIFEST） |
| archives/l/libics/manifest.yaml | 软件级元数据 |
| archives/l/libics/README.md | 软件说明 |

## 注意事项
- 本轮仅完成未提交工作树，未执行 commit/push，未创建 PR
- 真机预检通过前不得合入；代码再变化时本笔记验证结论同步失效

v2llllllll 2026-09-16: v1(IF TARGET ZLIB::ZLIB) preflight still failed identically (guard printed but crc32/deflate/inflate still undefined) -> root cause refined to case mismatch: CMakeDeps advertises lowercase find_package(zlib)/zlib::zlib which upstream never calls; v2 probes find_package(zlib CONFIG QUIET) explicitly and links whichever of zlib::zlib / ZLIB::ZLIB exists (PUBLIC).
