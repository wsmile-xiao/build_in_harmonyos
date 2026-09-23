# BCUnit 5.3.113 OHOS 适配笔记

> 适配日期:2026-09-10
> 分支:`feat/bcunit-5.3.113`
> 源码:https://github.com/BelledonneCommunications/bcunit/archive/refs/tags/5.3.113.tar.gz
> SHA-256:`9353fd915cdd071587d00b914e21eb4f64a63bb9fbe181fd05c4f82c256a38ba`
> 同软件前一版本:`archives/b/bcunit/3.0.2`(2017 年代内容,已发布)

## 1. 编译环境

- 构建系统:cmake(上游主构建系统;tag 归档另有 autotools 入口但无预生成 configure)
- 编译日期:2026-09-10
- 编译器:clang 15.0.4(target aarch64-unknown-linux-ohos)
- CMake 4.1.2 / GNU Make 4.4.1(make -j1)
- 状态:built

## 2. 软件概况

BCUnit 是 Belledonne Communications 维护的 C 单元测试框架(CUnit 的 fork),是
bctoolbox/Linphone 测试栈的依赖:

- 框架层 `BCUnit/Sources/Framework/`(CUError/MyMem/TestDB/TestRun/Util)
- 三个输出接口:Basic(stdout)/Automated(XML)/Console(交互),curses 默认关闭
- 无第三方依赖,仅链接 libc(W0:无外部依赖,无需 conan install 预检;
  `prescan` 的 PSCAN-MUSL-005 命中 `BCUnit/Headers/BCUnit_intl.h:38` 的
  `#include <libintl.h>`,该 include 位于文件内的注释块中(第 37-48 行
  `/* activate these when source preparation is complete ... */`),
  全仓库无 `ENABLE_NLS` 定义点,属不可达死代码,无需 NLS 处理)
- 许可证:LGPL v2 或更高(COPYING 及各源文件头)

### 2.1 为什么需要 5.3.113(版本语义)

bcunit 5.3.x/5.4.x 的 tag 是 linphone-sdk 锁步快照打在 bcunit 仓上的,内容里
`project(BCUnit VERSION "3.0.2")` 长期不变:

- tag `3.0.2`(2017 内容)与 tag `5.3.113`(SDK 5.3 线内容)**声明的版本号相同**,
  `find_package(BCUnit 3.0.2 REQUIRED)` 对两者都匹配,但 API 完全不同
- bctoolbox 5.3.115 的 tester 需要 5.3 线 API:实测 5.3.113 含
  `CU_Suite.pUserData`(`BCUnit/Headers/TestDB.h:164`)、
  `CU_automated_enable_partial_junit`(`BCUnit/Headers/Automated.h:88`)、
  `CU_set_trace_handler`(`BCUnit/Headers/Util.h:147`);3.0.2 内容缺前两项
- 因此本包以**内容时代**选版本:包目录/Conan 版本为 `5.3.113`,不按文件内声明的
  "3.0.2" 命名(否则与已有的 3.0.2 tag 内容包冲突且无法区分)

包形态:`package_type = "library"`;上游安装产物为 `include/BCUnit/*.h`、
`lib/libbcunit.a`(默认 shared=False)或 `lib/libbcunit.so`(shared=True)、
`lib/pkgconfig/bcunit.pc`、`share/BCUnit/*.dtd|*.xsl` 与
`share/BCUnit/cmake/BCUnitConfig.cmake`。无任何可执行文件安装
(库类型包,无 commands.json)。

库类型由 Conan toolchain 的 `BUILD_SHARED_LIBS` 驱动:上游 5.3.113 已把
3.0.2 的 `ENABLE_STATIC`/`ENABLE_SHARED` 双目标改成单个裸
`add_library(bcunit ${SOURCE_FILES})`(`BCUnit/Sources/CMakeLists.txt:158`),
`CMakeToolchain` 的 SharedLibBlock 会按 `shared` 选项写入该变量。

## 3. 编译步骤

### 3.1 原生探索(补丁后源码,无任何额外平台参数)

```sh
cmake -S src -B build -DCMAKE_BUILD_TYPE=Release -DENABLE_BCUNIT_TEST=ON \
  -DCMAKE_INSTALL_PREFIX=<prefix>
make -j1
./BCUnit/Sources/Test/test_bcunit   # 上游自带内部自测
```

### 3.2 Conan 构建

`conan create` 按 conanfile.py 执行:CMakeToolchain(BUILD_SHARED_LIBS 由
shared 选项驱动,ENABLE_BCUNIT_TEST=ON,EXAMPLES/DOC/CURSES=OFF)→
apply_conandata_patches → cmake.configure/build → 在 build() 内直接运行上游
自测程序 test_bcunit(断言计数进入 create 日志)→ package() cmake.install()
并锚定 bcunit.pc 内的相对路径;test_package 消费者自动编译运行。

build() 的测试执行带计数断言:上游 `test_bcunit.c` 的 `main()` 无条件
`return 0;`,`self.run` 的退出码无法反映断言回归,因此配方把测试输出同时
`tee` 到 build folder 的 `upstream-self-test.log`,解析
`Total Number of Assertions` 与 `Failures` 并断言 `3915 / 0`
(`UPSTREAM_TEST_ASSERTIONS`),不符即 `ConanException` 让构建失败;
`package()` 的 `bcunit.pc` 路径锚定同样逐条断言上游模板模式存在(失配即报错,
不再静默产出相对路径 `.pc`)。

## 4. 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `-DENABLE_BCUNIT_TEST=ON` 时 `bcunit_test` 编译报 `fatal error: 'BCUnit_intl.h' file not found`(CUError.c:40) | 5.3.113 把框架头文件目录从顶层全局 `include_directories(BCUnit/Headers ...)` 改成只挂在 `bcunit` 目标上的 `target_include_directories()`;`bcunit_test` 目标仍只保留 `Test` 一个相对目录,拿不到源码 Headers 与生成目录(BCUnit.h) | 给 `bcunit_test` 补上 `${PROJECT_SOURCE_DIR}/BCUnit/Headers` 与 `${PROJECT_BINARY_DIR}/BCUnit/Headers`(patches/0001);不改动库目标与全局作用域 |
| 2 | 修好后链接 `test_bcunit` 报 `undefined symbol: CU_trace_handler`(libbcunit_test.a 的 Util.c.obj:otherPrintf) | trace 回调全局变量存储定义在接口文件 `Basic/Basic.c:64`,框架文件 `Util.c:110` 只 extern 引用;`bcunit_test` 静态库只含 5 个框架源文件不含 Basic.c → 符号必然未定义。CMake 与 autotools 两条构建路径同构,任何平台可复现,属上游架构性缺陷而非平台问题(与 3.0.2 同型) | 存储定义移入 `Framework/Util.c`(extern 声明处),Basic.c 改为 extern 声明(patches/0002);`CU_set_trace_handler()` 公共 API 位置不变,导出符号集合与 ABI 不变,无平台条件编译 |

关于问题 2 的运行时复核:test_package 消费者安装 `CU_set_trace_handler()` 探针
后运行 basic 接口,探针被框架自身输出路径调用 11 次(见 §7.2),证明该符号在
Conan 包内确实可用且被框架引用,而不只是"链接通过"。

### 4.1 上游既有缺陷(不属本包修复范围,记录备查)

`CU_automated_run_tests()` 在同一进程内第二次调用必然 SIGSEGV
(`initialize_result_file()` 之前的既有状态即已损坏),与本次两个补丁无关:

- 复现:同一进程 basic 运行 + 两次 automated 运行 → 第一次 automated 正常出报告,
  第二次崩溃;`automated_enable_partial_junit` 开/关均可复现
- 用**未打补丁的原始 5.3.113 源码**单独构建的库同样复现(见 §7.4 原始库对照),
  故非适配引入
- 同一进程内 basic 接口可重复运行,basic 与 automated 任意先后各一次均正常
- 处置:包侧不做修改(上游缺陷);test_package 需要覆盖两种 JUnit 模式时用
  **两次进程调用**规避,并在 test.c/MANIFEST.yml 注明

## 5. 源码修改

两个补丁,均为 GNU diff -u 生成(a/ b/ 前缀),`patch_ng.fromfile(...).apply(strip=1)`
在 pristine 副本上回放通过,回放结果与探索目录逐字节一致
(`diff -r` 无差异,见 §7.4 证据);conandata.yml 按 Conan 官方列表结构声明,
补丁描述不含逗号。

| 文件 | 内容 |
|------|------|
| patches/0001-fix-bcunit-test-include-directories.patch | `BCUnit/Sources/CMakeLists.txt`:`bcunit_test` 目标补上框架源码/生成 Headers 目录 |
| patches/0002-move-cu-trace-handler-to-framework.patch | `Framework/Util.c` 增加 `bcunit_trace_handler_t CU_trace_handler = NULL;`;`Basic/Basic.c` 该定义行改为 extern 声明 |

上游测试零修改:仅修复构建/链接缺陷使测试程序可生成运行,测试源
(`BCUnit/Sources/Test/test_bcunit.c`)与断言逻辑无任何改动。

## 6. 依赖版本

无第三方依赖(仅 libc)。W0:依赖集为空,无 conan install 预检项;
`conanfile.py` 的 `requirements()` 为空实现。

## 7. 验证结果

### 7.1 上游测试(设备实测,统计单位=断言;程序末尾自打印;exit code 0)

```text
Testing BCUnit internals...
     testing CUError.c ... 15 assertions, 0 failures
     testing MyMem.c ... 34 assertions, 0 failures
     testing TestDB.c ... 893 assertions, 0 failures
     testing TestRun.c ... 2836 assertions, 0 failures
     testing Util.c ... 137 assertions, 0 failures

---------------------------
BCUnit Internal Test Results
---------------------------
  Total Number of Assertions: 3915
     Successes: 3915
     Failures: 0
```

- TOTAL=3915 PASS=3915 FAIL=0 SKIP=0 NOT_RUN=0,通过率 3915/3915=100%
- 取数命令:`./BCUnit/Sources/Test/test_bcunit | grep 'Total Number of Assertions'`
- 分母口径:上游唯一自带测试程序就是 test_bcunit(自测试框架不能用 BCUnit 测
  自身,采用内嵌断言计数);Examples(AutomatedTest/BasicTest/ConsoleTest 等)
  是演示程序,不计入上游用例分母
- SKIP=0、无 #ifdef 整组未编译用例(测试代码由 ENABLE_BCUNIT_TEST 显式开启,
  启用即全量)
- 同一组计数在 `conan create` 的 `build()` 内被配方断言(§3.2):不符
  `3915 / 0` 即构建失败,因此 CI 轮的上游测试证据不是"跑过就算",而是带门控

### 7.2 test_package 消费者(同一二进制两次调用,统计单位=进程调用)

```text
bcunit smoke [full]:    tests_run=3 failures=0 asserts=6 checks=6 failed_checks=0 trace_calls=11
bcunit smoke [partial]: tests_run=2 failures=0 asserts=4 checks=4 failed_checks=0
```

- full 模式:registry/suite/3 用例 + `CU_Suite.pUserData` 回读;basic 接口计数
  3/3、失败 0、断言 6;automated 接口输出完整 JUnit 报告(含 `<testsuites>` 与
  `<testsuite>`);`CU_set_trace_handler()` 探针被调用 11 次
- partial 模式:`CU_automated_enable_partial_junit(CU_TRUE)` 后报告不含
  `<testsuites>`、仍含 `<testsuite>`,运行 2 用例失败 0
- 两种模式 exit 0,共 10 项检查全部通过;JUnit 输出文件写在 Conan build folder
  (conanfile 显式设置 cwd),不落包源目录

### 7.3 库形态与产物

- 静态(默认 shared=False):`lib/libbcunit.a`,静态链接消费者运行通过
- 动态(shared=True):`lib/libbcunit.so`,消费者 `DT_NEEDED = libbcunit.so`
  运行通过;`readelf -d` 显示 `BIND_NOW`/`FLAGS_1 NOW`,无系统同名库冲突(G3)
- 实测 `libbcunit.so` 无 SONAME 标记:设备 `uname` 为 HarmonyOS,裸 CMake
  探测命中无对应 Platform 模块的系统名,VERSION 属性因而不生成版本化
  soname;链接器按文件名解析,静态/动态消费均不受影响(与 3.0.2 结论一致)
- `bcunit.pc` 上游按相对目录生成(`prefix=`、`exec_prefix=bin`、`libdir=lib`、
  `Libs: -Llib -lbcunit`),配方在 `package()` 中锚定为包内绝对路径

### 7.4 证据文件

| 证据 | 路径(任务私有 `$HOME/tmp/bcunit-5.3.113/`) |
|------|------|
| 源码校验 | `bcunit-5.3.113.tar.gz` sha256 9353fd91…(官方 tag 归档,与 conandata 一致) |
| 原生 configure/build/install | `native-configure-1.log`、`native-build-1..3.log`、`native-install-1.log` |
| 首次真实错误(两轮) | `native-build-1.log`(BCUnit_intl.h file not found)、`native-build-2.log`(undefined symbol CU_trace_handler) |
| 上游测试输出 | `upstream-test-1.log`(3915 断言) |
| 补丁回放校验 | `patchverify/`(patch_ng strip=1 回放后 `diff -r` 与探索目录一致) |
| 原始源码对照(问题 4.1) | `build-pristine/`、`consumertest/probe*.err`(未打补丁库同样 SIGSEGV) |
| 消费者本地预验证 | `consumertest/`(静态/动态两种链接方式的运行输出) |
| Conan 干净构建与门禁 | `reports/conan-create.log`、`reports/conan-verify-supplement.md`(如生成) |

## 8. 注意事项

- 消费方式为 `#include "BCUnit/BCUnit.h"`(头文件装在 include/BCUnit/ 下),
  Basic/Automated/Console 接口头需另行 include(`BCUnit/Basic.h` 等)。
- 下游 bctoolbox 5.3.115 `find_package(BCUnit 3.0.2 REQUIRED)`:Conan toolchain
  固定 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`,该调用解析 CMakeDeps 生成的
  `bcunit-config.cmake`;上游自带的 `FindBCUnit.cmake` 成为死代码,下游依赖的
  `BCUnit_TARGET` 变量需在消费方 `generate()` 预置(见 bctoolbox 任务结论)。
- 补丁管理:`.build-context-*` 的 BUILD_SRC_DIR / BUILD_SRC_ORIG_DIR 指向
  pristine 副本,refresh-patch 走"无差异"安全路径,人工补丁不被改写。
- 同软件 3.0.2 与 5.3.113 内容差异集中在:CMake 目标化重构(补丁 0001 的起因)、
  选项改名(`ENABLE_*` → `ENABLE_BCUNIT_*`)、单目标 `add_library`、
  新增 `CU_registry_initialized`/`CU_get_run_results_string`/
  `CU_automated_enable_partial_junit`/`CU_Suite.pUserData` 等 API。
