# fff 1.1 适配笔记（HarmonyOS PC · header-only + 上游 Makefile 测试套件）

## 定位
- 单头文件 C/C++ fake 函数（mock）测试框架，产出仅 `include/fff.h`（380KB，由上游
  `fakegen.rb` 预生成），零外部依赖，无库/可执行产物。

## 源
- 上游 release tag v1.1：
  https://github.com/meekrosoft/fff/archive/refs/tags/v1.1.tar.gz
- sha256: 510efb70ab17a0035affd170960401921c9cc36ec81002ed00d2bfec6e08f385
  （github.com 与 codeload.github.com 双源下载哈希一致，设备实测）
- 许可证 MIT（fff.h 头部与 LICENSE 文件核实）。

## W0/W0b
- preflight_check.sh fff/1.1：无依赖声明，通过（header-only，零第三方依赖）。
- 本仓库无同软件历史归档（archives/f/ 无 fff 目录）；recipe-search 无相似配方
  （语料 4434 条），首稿按 templates/conanfile-headeronly.py.tmpl + utf8.h 先例编写。
- lang-preflight：task=C，detected 通过（C/C++ 兼容族，fff.h 为 C/C++ 双支持单头），
  milestone=lang_checked。

## 上游测试（R51 四维账本，v1.1 tag 源码注册入口逐项数）
- N_static：181（框架注册的原子用例，注册入口口径，来源分列）：
  - test/fff_test_c.c：36（main 中 RUN_TEST 逐条注册，c_test_framework.h 自制框架）
  - test/fff_test_global_c.c：35（同上）
  - test/fff_test_cpp.cpp：44（gtest 自动注册 = test_cases.include 41 + 自有 3；
    test_cases.include 共 42 个 TEST_F 定义，其中
    when_fake_func_called_then_const_arguments_captured 位于 `#ifndef __cplusplus`
    块，按上游条件编译设计仅 C 侧编译）
  - test/fff_test_global_cpp.cpp：41（gtest，test_cases.include C++ 生效子集）
  - examples：25 = embedded_ui/UI_test_ansic.c 10（RUN_TEST）+
    embedded_ui/UI_test_cpp.cpp 10（gtest TEST）+
    driver_testing/driver.test.cpp 2（TEST）+
    driver_testing/driver.test.fff.cpp 3（TEST_F）
- N_registered：11（上游构建注册的可执行测试目标，即上游 buildandtest 脚本逐个
  执行的 11 个二进制：fff_test_c / fff_test_cpp / fff_test_glob_c /
  fff_test_glob_cpp / ui_test_ansic / ui_test_cpp / driver_testing /
  driver_testing_fff / weak_linking test_display / test_sensor / test_main）。
  口径说明：11 是构建目标层（test/Makefile all 4 目标 + embedded_ui 2 个测试目标
  [template 非测试] + driver_testing 2 个测试目标 + weak_linking 3 个），与 181 个
  原子用例分属不同层级，不能混算。
- N_executed：181/181 全部通过（OHOS 真机原生 clang 执行，`[ RUN ]` 100、
  `[ FAILED ]` 0、C 侧 SUCCESS 行 81 = 36+35+10；gtest `[ PASSED ]` 44/41/10/2/3）。
  另有 weak_linking 3 个 assert 式单 main 程序（非框架注册，输出 `Test ... ok`）
  3/3 通过。
- 跳过分类：0 项跳过。11/11 目标全部在真机构建并执行。gtest 数字与静态定义差
  （45→44、42→41）系上游 `#ifndef __cplusplus` 条件用例，非环境跳过。
- N_consumer：1（test_package/test.c，22 个断言，22/22 通过，退出码 0）。
- 证据：reports/fff-1.1-conan-create-log.md（conan create 完整日志逐字转写，头部
  声明原始字节数/sha256/HEAD/命令）。

## 上游测试修改说明（未修改任何上游源文件）
上游测试源码、Makefile、buildandtest 一字未改。配方 build() 按上游 test/Makefile
与 examples Makefile 的语义用 OHOS 工具链等价复刻编译命令（R33：编译器经
`tools.build:compiler_executables` 从 Conan conf 取，替代上游硬编码 gcc/g++）：
1. C 目标：`clang -I<src> -O0 -g -Wall -std=c99`（上游同参）；
2. C++ 目标：`clang++ -std=c++17 -DGTEST_USE_OWN_TR1_TUPLE=1`（上游无 -std，
   此处与 profile cppstd=17 对齐；vendored gtest 编译一次供 5 个 gtest 目标复用）；
3. 不复刻链接参数 `-lpthread`：fff 测试代码未引用任何独立 pthread 符号，OHOS
   （musl）线程符号内建 libc，实测 11 个目标链接运行全部通过；
4. weak_linking：复刻 `-DFFF_GCC_FUNCTION_ATTRIBUTES="__attribute__((weak))"` 与
   libfakes.a 成员（上游 FAKE_OBJECTS 列表中 sensor.fake.o 重复一次，经 GNU make
   `$^` 去重后实际 5 成员：display/sensor/error/bus fake + test_common）；
5. include 路径：weak_linking 补 `-I examples/weak_linking/src`（上游 `./src/`）。

## 构建要点
1. header-only：`package_type="header-library"` + `package_id()` 清空 +
   package() 只装 include/fff.h 与 licenses/{LICENSE,README.md}。
2. 上游测试集成：`options = {"run_upstream_tests": [True, False]}`（默认 True），
   build() 内逐目标编译并按 can_run 执行，CI 与真机同路径（R51）。
3. fff.h v1.1 为新版宏实现（PP_NARG_MINUS1 可变参数派发）：实参历史字段按参数
   命名（`arg0_history`，非旧版 `arg_history`）；`fff.call_history` 存 fake 函数
   指针（上游断言口径 `(void*)funcname`）——消费者测试初版两处按旧版字段书写
   被编译器/断言当场拦下，已修正（这正是消费者测试的价值）。

## 消费者测试（test_package/test.c，R34）
单翻译单元消费者：`DEFINE_FFF_GLOBALS` + FAKE_VOID_FUNC/FAKE_VALUE_FUNC 定义
fake，22 个断言覆盖：call_count 初值与递增、arg0_val/arg0_history 实参捕获、
fff.call_history 全局调用顺序（函数指针口径）、值函数默认返回 0、return_val_seq
序列与耗尽后重复最后元素、custom_fake 接管、RESET_FAKE 零化语义、
FFF_RESET_HISTORY() 清全局历史。断言失败计数决定退出码（0=全过）。

## 路径 B 判断（首次真实构建后，AGENTS §6.2）
结论：不走路径 B，纯路径 A。依据：
1. 适配无跨仓库复用的新知识增量：header-only 品类已有框架模板
   （templates/conanfile-headeronly.py.tmpl，v12.21）与已合入先例（utf8.h）覆盖；
   本包配方一次通过 G2（此前失败均为我方配方书写/消费者测试字段名问题，非 OHOS
   平台特性，不构成可复用错误模式）。
2. 知识库查重：recipe-search 无相似配方；构建过程中知识图谱引擎命中 E540/E364
   均为既有条目（HNP 工具路径/测试簇分账），无新增价值。
3. 无已穷尽方案的失败分析：11/11 上游目标 + 消费者测试全部通过，不存在
   "部分/无法适配"类成果。
（是否走 B 的最终决定与 Issue 创建由主理 agent 收口；本条为判断依据与证据记录。）

## 状态
built —— conan-verify G0/G1/G2/G3/G4/L2/L4/L5 全过（verdict=PASS），消费者
22/22 通过（见 reports/）。
---

**编译结束**: 2026-09-12 04:31
**最终状态**: built
