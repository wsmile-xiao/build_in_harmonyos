# BCUnit 3.0.2 OHOS 适配笔记

> 适配日期:2026-09-06
> 分支:`feat/bcunit-3.0.2`
> 源码:https://github.com/BelledonneCommunications/bcunit/archive/refs/tags/3.0.2.tar.gz
> SHA-256:`eb7090aca5006aa0cea425722cb3fa1a7139185a7d9d1734d57844f69084713f`

## 1. 编译环境

- 构建系统:cmake(上游主构建系统;tag 归档另有 autotools 入口但无预生成 configure)
- 编译日期:2026-09-06
- 编译器:clang 15.0.4(target aarch64-unknown-linux-ohos)
- CMake 4.1.2 / GNU Make 4.4.1(make -j1)
- 状态:built

## 2. 软件概况

BCUnit 是 Belledonne Communications 维护的 C 单元测试框架(CUnit 的 fork,2017 年
3.0.2 后停更),是 bctoolbox/Linphone 测试栈的依赖:

- 框架层 `BCUnit/Sources/Framework/`(CUError/MyMem/TestDB/TestRun/Util)
- 三个输出接口:Basic(stdout)/Automated(XML)/Console(交互),curses 默认关闭
- 无第三方依赖,仅链接 libc(W0:无外部依赖,无需 conan install 预检)
- 许可证:LGPL v2 或更高(COPYING 及各源文件头)

包形态:`package_type = "library"`;上游安装产物为 `include/BCUnit/*.h`、
`lib/libbcunit.so`(VERSION 1.0.1 属性)、`lib/libbcunit.a`、
`lib/pkgconfig/bcunit.pc`、`share/BCUnit|BCunit/` DTD/XSL 与 CMake config。
无任何可执行文件安装(库类型包,无 commands.json)。

## 3. 编译步骤

### 3.1 原生探索(补丁后源码,无任何额外平台参数)

```sh
cmake -S src -B build -DCMAKE_BUILD_TYPE=Release -DENABLE_TEST=ON \
  -DCMAKE_INSTALL_PREFIX=<prefix>
make -j1
./BCUnit/Sources/Test/test_bcunit   # 上游自带内部自测
```

### 3.2 Conan 构建

`conan create` 按 conanfile.py 执行:CMakeToolchain(ENABLE_SHARED/STATIC 映射
shared 选项,ENABLE_TEST/EXAMPLES/DOC=OFF)→ apply_conandata_patches →
cmake.configure/build → cmake.install;test_package 消费者自动编译运行。

## 4. 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1.2 configure 报 `Compatibility with CMake < 3.5 has been removed` | 2017 年代上游声明 `cmake_minimum_required(VERSION 2.8.12)`;CMake 4.x 移除 <3.5 兼容 | 最小版本提升到 3.5(patches/0001),仅改声明行不改策略行为 |
| 2 | `-DENABLE_TEST=ON` 时上游自测程序链接报 `undefined symbol: CU_trace_handler`(Util.c.obj:(otherPrintf) in libbcunit_test.a) | trace 回调全局变量存储定义在接口文件 `Basic/Basic.c`,框架文件 `Util.c` extern 引用它;`bcunit_test` 静态库只含 5 个框架源文件不含 Basic.c → 符号必然未定义。CMake 与 autotools 两条构建路径同构,任何平台可复现,属上游架构性缺陷而非平台问题 | 存储定义移入 `Framework/Util.c`(extern 声明处),Basic.c 改为 extern 声明(patches/0002);`CU_set_trace_handler()` 公共 API 位置不变,导出符号集合与 ABI 不变,无平台条件编译 |

llvm-nm 逐对象核对:libbcunit_test.a 除 CU_trace_handler 外,其余交叉引用
(TestDB↔TestRun)均可库内自解析。

## 5. 源码修改

两个补丁,均为 GNU diff -u 生成(a/ b/ 前缀),pristine 副本 `patch -p1 --dry-run`
回放通过;conandata.yml 按 Conan 官方列表结构声明:

| 文件 | 内容 |
|------|------|
| patches/0001-cmake-minimum-version-3.5.patch | CMakeLists.txt:cmake_minimum_required 2.8.12 → 3.5 |
| patches/0002-move-cu-trace-handler-to-framework.patch | Util.c 增加 `bcunit_trace_handler_t CU_trace_handler = NULL;`;Basic.c 该定义行改为 extern 声明 |

上游测试零修改:仅修复链接缺陷使测试程序可生成,测试源与断言逻辑无任何改动。

## 6. 依赖版本

无第三方依赖(仅 libc)。W0:依赖集为空,无 conan install 预检项。

## 7. 验证结果

### 7.1 上游测试(设备实测,统计单位=断言;程序末尾自打印;exit code 0)

```text
Testing BCUnit internals...
     testing CUError.c ... 15 assertions, 0 failures
     testing MyMem.c ... 34 assertions, 0 failures
     testing TestDB.c ... 893 assertions, 0 failures
     testing TestRun.c ... 2836 assertions, 0 failures
     testing Util.c ... 137 assertions, 0 failures
  Total Number of Assertions: 3915
     Successes: 3915
     Failures: 0
```

- TOTAL=3915 PASS=3915 FAIL=0 SKIP=0 NOT_RUN=0,通过率 3915/3915=100%
- 取数命令:`./BCUnit/Sources/Test/test_bcunit | grep 'Total Number of Assertions'`
- 分母口径:上游唯一自带测试程序就是 test_bcunit(自测试框架不能用 BCUnit 测
  自身,采用内嵌断言计数);Examples(AutomatedTest/BasicTest/ConsoleTest 等)
  是演示程序,不计入上游用例分母
- SKIP=0、无 #ifdef 整组未编译用例(测试代码由 ENABLE_TEST 显式开启,启用即全量)

### 7.2 test_package 消费者

自建消费者注册 registry/suite/2 个用例,CU_basic_run_tests 运行后校验
tests_run=2、failures=0,exit 0;二进制输出到 build folder,不落包源目录。

## 8. 注意事项

- 实测包内 `libbcunit.so` 无 SONAME 标记,NEEDED 按文件名 `libbcunit.so`
  解析;静态链接与 conanrun 环境加载均不受影响,无系统同名库冲突(G3)。
  机制(2026-09-06 独立审计复核):本机 uname 为 HarmonyOS,裸 CMake 探测
  (host==target 时 conan 工具链不设 CMAKE_SYSTEM_NAME)命中无对应 Platform
  模块的系统名,VERSION 属性因而不生成版本化 soname;CMake 4.1.2 自带
  `Platform/OHOS.cmake`(继承 Linux),显式 `-DCMAKE_SYSTEM_NAME=OHOS` 时
  会正常生成 SONAME——若下游需要 soname,在工具链层显式指定即可。
- 消费方式为 `#include "BCUnit/BCUnit.h"`(头文件装在 include/BCUnit/ 下)。
- 补丁管理:`.build-context-*` 的 BUILD_SRC_DIR / BUILD_SRC_ORIG_DIR 均指向
  pristine 副本,refresh-patch 走"无差异"安全路径,人工补丁不被改写。
- 下游(bctoolbox)若以 shared 方式消费,链接器按文件名解析 libbcunit.so,无
  soname 依赖问题;若静态链接,`-lbcunit` 即可。
