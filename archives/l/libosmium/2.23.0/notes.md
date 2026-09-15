# libosmium 2.23.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMake；配方测试阶段使用逐 TU 直编驱动，见下）
- 编译日期: 2026-09-08
- 编译器: clang/clang++ 15（OHOS NDK，profile ci/conan/profiles/ohos-aarch64）
- Conan: 2.29.1
- 状态: built

## W0 依赖发布检查（全部已发布，conan download 实测）
- protozero/1.8.2（PBF 解析必需）
- zlib/1.3.1（gzip 压缩）
- bzip2/1.0.8（bzip2 压缩）
- lz4/1.10.0（lz4 压缩；1.9.4 无配方）
- expat/2.8.2.1.1（XML IO；2.6.x 及更早版本无配方，最新为 2.8.2 系）
说明：libosmium 的功能头文件无条件 `#include <zlib.h>/<bzlib.h>/<lz4.h>/<expat.h>/protozero`，
五个依赖必须全部随包传播（header-only 包也必须有 requires）。

## W0b 历史经验核验
上游仓库无同软件历史归档（archives/l/libosmium 仅有 2.20.0，与 2.23.0 不同版本目录，无冲突）。

## 语言预检（R47）
lang-preflight 通过（milestone=lang_checked），C++ 主体与声明语言 cpp 一致。

## 配方要点
- package_type = "header-library"（§12.11 教训：header-only 不能声明为 library）。
- requires 五依赖 + cpp_info.requires 传播；cpp_info.libs = []。
- 上游测试：test/CMakeLists.txt 注册 94 个单元测试（add_unit_test），框架为上游内置
  Catch v2.13.10（test/catch/catch.hpp + test_main.cpp CATCH_CONFIG_MAIN），零外部测试依赖。
- 配方 build() 生成 run_upstream_tests.sh：按上游 test/CMakeLists.txt 的注册清单逐 TU 编译
  91 个测试可执行文件（4 路并发）并逐个运行，逐用例退出码 0（Catch fail-only 语义，通过时输出 All tests passed）。
  GEOS/GDAL 门控的 3 项（geom test_geos test_ogr test_ogr_wkb）按上游 ENABLE_IF 语义跳过。
  Boost 仅上游 CMake 的 examples/benchmarks 需要，单元测试源零引用（grep 证实），驱动不引入。
- BUILD_DATA_TESTS 上游 tarball 默认 OFF（dev_build 探测关闭），按上游默认不执行。
- 测试链接按上游 LIBS 条件：ZLIB_* → -lz；BZIP2_* → -lbz2；OSMIUM_XML_LIBRARIES → -lexpat；
  OSMIUM_PBF_LIBRARIES → protozero（header-only）；Threads → -pthread。

## 上游测试账本
- N_static = 94（test/CMakeLists.txt add_unit_test 注册数 = test/t 下 test_*.cpp 文件数，
  上游 CMake 自带 glob 自检确认 94/94 全部注册）
- N_executed = 91（94 - 3 项 GEOS/GDAL ENABLE_IF 条件跳过，制品仓无 GEOS/GDAL）
- N_passed = 91（逐用例 "All tests passed" + 退出码 0，逐用例日志见构建目录 testlogs/）
- N_failed = 0；N_skipped = 3（上游条件跳过：GEOS/GDAL 依赖不可得）
- data-tests（BUILD_DATA_TESTS）与 benchmarks/examples：上游默认 OFF，不属于默认测试口径。

## 消费者测试（test_package）
1 个消费者程序：OSMNode id/version/timestamp/location/user 真实 API 断言 +
LIBOSMIUM_VERSION_STRING 版本契约，共 8 处 CHECK，通过 8/8。

## 遇到的问题与解决（最终实测五项）
1. conan 2.29.1 依赖 cpp_info（_Component）无 aggregated_* 方法 → 手动聚合根+components 的
   includedirs/libdirs/libs。
2. PBF/XML 测试欠链接：FindOsmium 把 zlib 同时放进 OSMIUM_PBF_LIBRARIES 与 OSMIUM_XML_LIBRARIES，
   按 ENABLE_IF 拆分链接会漏 -lz（undefined inflate/uncompress）→ 全部测试统一链接
   zlib+bzip2+expat（首启门控/测试二进制 harmless over-link）。
3. OHOS musl 忽略 DT_RUNPATH 且 conanbuild 的 LD_LIBRARY_PATH 不含 expat（实测探针）→ 驱动
   运行前显式 export LD_LIBRARY_PATH=五个依赖的 lib 目录。
4. index 组 4 项 "tempfile failed: Permission denied"：create_tmp_file() 用 std::tmpfile()，
   musl 硬编码 /tmp（本平台只读）→ 补丁 0001-use-mkstemp-in-tmpfile：mkstemp(TMPDIR)+立即
   unlink 保留 tmpfile 语义（与 castget 先例同款修法）。
5. 消费者测试两处 API 认知修正：对象类为 osmium::Node（非 OSMNode）且构造函数私有，须用
   builder 模式（NodeBuilder/add_node）在 memory::Buffer 内创建。
另：设备高负载期 91 个 TU 编译超 3600s 默认预算 → `timeout set libosmium 2.23.0 10800`
（ci/config/build_timeouts.txt 本地修改不进 PR；CI worker 空载默认预算足够）。

## 验证结果
- conan-verify：G0/G1/G2/G3/G4/L2/L4/L5 通过（2026-09-08）。
- 上游测试：91/91 执行通过（94 注册，3 项上游条件跳过）。
- 消费者测试：1/1（NodeBuilder 真实 API 往返 8 处 CHECK + 版本契约）。
- 补丁：patches/0001-use-mkstemp-in-tmpfile.patch（portability，无平台宏）。

## 交付物
| 文件 | 说明 |
|------|------|
| include/osmium/** | libosmium 头文件（header-only） |
| licenses/LICENSE | BSL-1.0 许可证 |

## 注意事项
- 消费者工程需同时可见五个依赖的头文件（cpp_info.requires 已传播；CMakeDeps 消费方直接
  find_package(libosmium) 即可）。
- libosmium 自带 cmake/FindOsmium.cmake 模块路径依赖（find_package(Osmium)）仅上游构建使用；
  Conan 消费走 CMakeDeps 生成的 libosmium config。
---

**编译结束**: 2026-09-11 01:33
**最终状态**: built
