# flatbuffers 25.12.19 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-08
- 编译器: clang/clang++ 15（OHOS NDK，profile ci/conan/profiles/ohos-aarch64）
- Conan: 2.29.1（os=OHOS 适配版）
- 状态: built

## W0 依赖发布检查
flatbuffers 库与 flatc 工具自包含，无外部依赖；`preflight_check.sh` 通过（无依赖需检查）。

## W0b 历史经验核验
`archives/f/flatbuffers/24.3.25` 仅含 manifest.yaml + notes.md（Conan 化之前的历史归档，无配方）。
其 CMake 经验（FLATBUFFERS_BUILD_TESTS=OFF/FLATC=ON 可构建）作为参考；本轮按 R51 要求改为
开启上游测试并在构建内执行。历史 GitHub 超时问题通过 conan 下载缓存（按 SHA256 预置）解决。

## 语言预检（R47）误报取证
lang-preflight 判 env_unsupported（rust:163/python:123/java:122/nodejs:97，"主体占比 23%"）。
实为多语言绑定/测试资产污染源码统计：顶层构建系统为 CMake（仅编译 C++），C++ 主体为
include/ 35 个头文件 + src/ 55 个源文件 + grpc/ 15 个 C++ 文件 + tests/ 50 个 C++ 测试文件；
rust/python/java/js 目录均为跨语言绑定与测试，不进入 CMake 构建。按 smashtable（!8487）/
tinydng（!8399）先例判误报，继续按 cpp 适配，result.json 以真实终态覆盖。

## 配方要点
- 静态库 libflatbuffers.a + 模式编译器 flatc + CMake package config（cmake.install()）。
- options: shared/fPIC/flatc；R26 默认静态。
- FLATBUFFERS_BUILD_TESTS=ON、FLATBUFFERS_BUILD_CPP17=ON：build() 内直接运行 flattests 与
  flattests_cpp17（R51 三步法，CI 与真机同路径）。
- 软件级 commands.json（flatc 命令行工具，PF8）。

## 上游测试账本
| 套件 | 注册数（直接调用层） | 执行 | 结果 |
|------|--------|------|------|
| flattests（tests/test.cpp） | 102（FlatBufferTests 直接调用 96 + main 内 FlatBufferBuilderTest 展开的 6 个套件调用：3×BuilderTests::all_tests + 3×BuilderReuseTests::run_tests） | 102 | ALL TESTS PASSED，退出码 0 |
| flattests_cpp17（tests/cpp17/test_cpp17.cpp） | 3（FlatBufferCpp17Tests 体内直接调用 CreateTableByTypeTest/OptionalScalarsTest/StringifyAnyFlatbuffersTypeTest） | 3 | C++17: ALL TESTS PASSED，退出码 0 |
| grpctest | 上游默认 OFF，需外部 gRPC（GRPC_INSTALL_PATH + gRPC::grpc++_unsecure，制品仓无） | 0 | 按上游默认配置不构建不执行 |
| 合计 | 105 | 105 | 0 失败 0 跳过（默认构建口径，单一"直接调用层"颗粒度） |

上游 runner 为 fail-only 口径（仅打印失败数，无逐用例通过输出），"ALL TESTS PASSED" 且
退出码 0 即全部注册测试通过；账本采用单一"直接调用层"颗粒度：FlatBufferTests 函数体 96 个
直接调用 + FlatBufferBuilderTest 体内 6 个套件调用 + FlatBufferCpp17Tests 体内 3 个直接调用。

## 关键问题与解决：FLATBUFFERS_LOCALE_INDEPENDENT
- 现象 1（首轮）：test_package 链接失败 `undefined symbol: flatbuffers::ClassicLocale::instance_`。
  根因：上游 CMakeLists 用目录级 `add_definitions(-DFLATBUFFERS_LOCALE_INDEPENDENT=$<BOOL:...>)`
  注入宏，不随安装导出；消费者头文件在 OHOS（_XOPEN_VERSION>=700）默认宏=1，引用了库未编译的
  ClassicLocale::instance_。
- 现象 2（强制宏=1 时）：上游 parser_test.cpp:483 失败——hex-float 字面量 "0x12.34p-1" 被解析为
  invalid number。微观探针（probe_loc）定位：OHOS libc 的 strtod_l 在传入 ClassicLocale 创建的
  locale 对象时只消费 "0" 即停止；传 newlocale(LC_ALL_MASK,"C",0) 新建对象或用裸 strtod 均正常
  （9.101562）。
- 解决：配方显式 `FLATBUFFERS_LOCALE_INDEPENDENT=OFF`（上游探测式在本工具链同样落 0），并在
  `package_info()` 导出 `cpp_info.defines=["FLATBUFFERS_LOCALE_INDEPENDENT=0"]`，库与消费者走同
  一条 plain-strtod 路径；第 4 轮 conan-verify 全门禁通过（当时按 97+1 混层口径记 98，后经 W4
  审计纠正为直接调用层 105，见"上游测试账本"）。
- 陷阱记录：conan 按 package_id 复用 build 文件夹且 CMake CACHE 变量无 FORCE，第 3 轮显式 OFF 被
  第 2 轮残留 ON 覆盖（CMakeCache 实证），清空 p/b/<pkgid> 后复现消失。

## 验证结果
- conan-verify：G0/G1/G2/G3/G4/L2/L4/L5 全部通过（2026-09-08 第 4 轮）。
- 消费者 test_package：1/1 通过——FlatBufferBuilder/CreateVector/GetRoot<Vector> 往返 +
  flexbuffers map 往返共 10 处 CHECK；另运行打包产物 flatc 并 grep 断言版本输出。
- 上游测试：105/105（如上表）。

## 交付物
| 文件 | 说明 |
|------|------|
| include/flatbuffers/*.h | 库头文件 |
| lib/libflatbuffers.a | 静态库（默认） |
| bin/flatc | 模式编译器（L2 烟雾 --version 通过） |
| lib/cmake/flatbuffers/ | CMake package config |

## 注意事项
- 消费者工程若自行注入 FLATBUFFERS_LOCALE_INDEPENDENT=1 将在 OHOS 上触发 hex-float 解析差异，
  请保持跟随本包导出的 =0。
- flatc 选项关闭时上游测试随之关闭（测试需 flatc 做代码生成）；默认 flatc=ON。
- grpctest 解除条件：gRPC 以可解析版本进入制品仓后，可按 skiparray upstream_tests 模式接入。

## 最终状态

- 状态: built（conan-verify 全门禁 G0-G4/L2/L4/L5 通过，W3 本地 CI 模拟通过）
- 上游测试: 105/105（直接调用层单一颗粒度；grpctest 上游默认 OFF 不计入）
- 消费者测试: 1/1（10 处 API CHECK + flatc 运行断言）
- 交付物: include/flatbuffers 头文件、lib/libflatbuffers.a、bin/flatc、lib/cmake/flatbuffers
- COMPLETED
