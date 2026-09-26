# unittest 0.50-62 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，生成文件随包发布，无需 autoreconf）
- 上游：https://unittest.red-bean.com/（C++ Unit Test Framework，BSD-3-Clause）
- 版本语义：0.50 为 `AC_INIT` 版本，62 为 tarball 修订号（包内 `print-version`
  脚本恒输出 `62`；Homebrew stable 同为 `0.50-62`）
- 源码包：`unittest-0.50-62.tar.gz`，sha256
  `9586ef0149b6376da9b5f95a992c7ad1546254381808cddad1f03768974b165f`
 （与 Homebrew 官方公式交叉核对一致，并经本地下载实测验证）
- 编译器: clang/clang++（OHOS aarch64 真机，待预检确认版本）
- 状态: 首轮工作树，真机预检待执行

## 上游结构审计（解包实测）
- `lib/`：UnitTest.cpp、Suite.cpp、Registry.cpp、SigHandler.cpp →
  构建 `libunittest.a`（`lib/Makefile.in: all: libunittest.a`）
- `test/`：unittesttest.cpp + 6 个 `*Test.cpp` + Helper →
  构建 `test/unittesttest`，`test/Makefile.in: test: unittesttest` 且自动执行
  `./unittesttest`
- 顶层 `Makefile.in`：`all: test`，`install: test`（先跑测试再安装）；
  安装内容：`include/*.hpp/*.tpp → $(includedir)/unittest/`、
  `lib/libunittest.a → $(libdir)/`、docs → `$(datadir)/unittest/`
- `make check`/`ctest` 不存在；`make` 即运行完整上游测试
- `configure.ac`：`AC_PROG_CXX` + `AC_CHECK_HEADERS([execinfo.h])`；
  `configure` 与 `print-version` 均带 +x 位（tar 实测 `rwxr-xr-x`）
- `Makefile.utils.in`：`CFLAGS = @CFLAGS@ -Wall -Werror`（上游自带 `-Werror`；
  Homebrew 以 Apple Clang 构建通过，OHOS clang 行为待预检确认）
- 公共 API（消费者测试依据）：`UnitTest.hpp`（ASSERT/ASSERT_EQUALS/
  ASSERT_EXCEPTION/FAIL 宏，Suite/Test/TestPtr，radix，createSuite/
  createNonSuite）、`Registry.hpp`（Registry::add/run）、
  `ExistingBase.hpp`（ExistingBase/ExistingObject）

## 上游测试清点（静态审计，63 叶子 + 6 套件容器 = 69）
- `ExistingBaseTest.cpp`：Count、Destructor = 2
- `RegistryTest.cpp`：Zero、One、Two、Missing、ArgsFirst、PassFail、Stream、
  StatusBad、StatusGood、Debug、DebugArg、List = 12
- `SuiteTest.cpp` All：Order、PassFailLeaf、PassFailSuite、Stream、StreamError、
  SetUpAssertionFailure、SetUpException、RunException、TearDownException、
  SetUpSignal、RunSignal、TearDownSignal、DivideByZero、Abort、BadAssertion、
  TemplatedNewTest、TemplatedNewTestArgs、TemplatedNewTestManyArgs、
  SetUpFailure、RunFailure、TearDownFailure、RunFailureNoDot = 22
 （RunOtherThreadFailure、DebugSignalBacktrace 被上游注释排除，不计入）
- `TestHolderTest.cpp`：Name、Stages、Assertions、ExceptionOnTearDown、Args = 5
- `TestPtrTest.cpp`：CreateDestroy、TwoRefs、MultipleRefs、Default、
  SimpleAssign、ComplexAssign、Dereference = 7
- `TestTest.cpp`：Assert、AssertEquals、AssertEqualsPtr、
  AssertEqualsStringChar、AssertEqualsStringString、AssertEqualsCharString、
  AssertEqualsCompareHelper、AssertEqualsCompareHelperInt、ExtraSpace、
  Name（TestPtr 式注册）、RadixDecimal、RadixHex、AssertException、
  AssertExceptionMessage、AssertionInOtherClass = 15
- 计数机制（`lib/Suite.cpp invokeOne`）：`passes_ += test->passes() + passed`，
  6 个 All 套件容器各贡献自身 1 pass；全绿汇总行应为
  `Tests finished with 69 passes and 0 failures.`（待真机确认）
- 无跳过机制：runner 无 `-skip` 语义（仅 `-debug/-list` 诊断开关）；
  致命信号 abort 路径会打印 `Fatal error when running tests.` 并计失败，
  配方将其判为失败（见 conanfile.py）
- `test/` 内无平台 `#ifdef`；唯一 `#ifdef HAVE_EXECINFO_H`（SigHandler
  崩溃栈回溯打印）不影响计数；musl 缺 execinfo 时 configure 自动降级

## OHOS 平台适配分析（零源码补丁的依据）
1. 语言期：纯 C++03（Homebrew 以 `-std=c++03` 构建；配方 `tc.cxxflags`
   同样追加），无 C++11+ 专属语法；`__PRETTY_FUNCTION__` clang 支持
2. 信号：SigHandler 用 sigaction + sigsetjmp/siglongjmp 捕获 SIGSEGV/
   SIGFPE/SIGABRT；上游测试以 `raise()` 注入信号（SuiteTest DivideByZero/
   Abort 等），非硬件 fault，AArch64 语义与 x86 一致，不存在
   “整数除零不触发 SIGFPE”类平台差异
3. 符号：`abi::__cxa_demangle`（`<cxxabi.h>`，libc++ 提供）用于测试名；
   execinfo 缺失仅关闭栈回溯打印
4. 构建：configure 仅做 `AC_PROG_CXX` 与头文件探测，无运行期探针；
   交叉编译安全；`print-version`/`configure` +x 位随包保留
5. 产物：上游只安装静态库，无 shared 规则 → 配方保留 shared/fPIC 选项
   但 `validate()` 拒绝 `shared=True`（与 unittestpp 同惯例）；
   静态库默认 `-fPIC` 供下游链接进共享库

## 编译步骤（配方实际执行）
1. `get()` 解包（strip_root）
2. `AutotoolsToolchain` 生成（CXXFLAGS += `-std=c++03 -fPIC`）
3. `configure`（conan 前缀，OHOS 工具链）
4. `make -j1 lib/libunittest.a test/unittesttest`（文件目标构建，不触发自动执行）+ OHOS 自签名 + 显式运行上游套件
   → 修正为 in-source 子目录构建：`make libunittest.a` 于 `lib/`、
   `make unittesttest` 于 `test/`（顶层无 `lib/libunittest.a` 目标，
   异地 VPATH 亦不可用；2026-09-24 真机 No rule 失败根因）
5. 显式重跑 `test/unittesttest`（日志捕获 → 汇总行解析 →
   `HMBS_UPSTREAM_TEST_RESULT` 双通道输出 → 失败/缺失/漂移抛错）
   → 2026-09-24 真机已输出 `Tests finished with 69 passes and 0 failures.`
   + `HMBS_UPSTREAM_TEST_RESULT={"status":"passed",...,"passed":69,...}`
6. `package()` 不再调用 `make install`，改为手动复制
   `lib/libunittest.a → lib/`、`include/*.hpp|*.tpp → include/unittest/` +
   `COPYING → licenses/`（问题 9；与上游 install 的消费者子集等效）
7. test_package：CMake 构建 `test_unittest`（`find_package(unittest)` +
   链接 `unittest::unittest`），运行并解析汇总行 →
   `HMBS_TEST_PACKAGE_RESULT` 双通道输出 → 非 8/0 抛错

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无 `make check`/ctest，如何满足“完整执行上游测试” | 上游以 `make` 默认目标直接运行测试二进制 | `make` 本身即测试运行器（失败即非零退出）；配方另显式重跑并解析汇总行，双重咽喉 |
| 2 | 汇总行 passes 的分母口径 | 框架按“叶子 + 套件容器”双层计数 | 静态审计 63 + 6 = 69，配方以 69 为期望值硬断言；真机确认后回填 |
| 3 | `-Wall -Werror` 在新 clang 下是否误伤 | 2015 年代码 + 现代告警；2026-09-24 预检命中：`test/ExistingBaseTest.cpp:94/97` 的 `std::auto_ptr` 被 OHOS libc++ 标记 deprecated，`-Werror,-Wdeprecated-declarations` 直接 Error 2 | 最小化豁免：构建脚本中把裸 `-Werror` 原地扩展为 `-Werror -Wno-error=deprecated-declarations`（幂等；configure 前后各一次，覆盖 `Makefile.utils.in` 与生成的 `Makefile.utils`；其余 `-Werror` 保留，不改源码与测试口径）。注：`tc.cxxflags` 追加无效，因 `-Wall -Werror` 写在 `@CFLAGS@` 之后会覆盖它，故必须改构建脚本 |
| 4 | 真机 configure 重 exec 报 `/data/service/hnp/bin/bash: inaccessible or not found`（2026-09-23 预检，config.status 生成后即错） | 仓库 profile `[buildenv]` 把 `CONFIG_SHELL/SHELL` 钉死到该绝对路径，本轮 runner 上不存在；conanbuild.sh 在 Python env 之后重导出坏值，仅设 `os.environ` 盖不住 | 按经验 2 最小适配：按存在性探测 `/bin/sh`→`/system/bin/sh`（不复用坏值）；generate 经 `tc.environment()` + `hmbs_tmp` build-scope 脚本持久化；build 前后各清理一次 source/build 树下 configure、config.status、libtool、Makefile 与 `.sh` 中的坏字面量；用可用 shell 显式调用 configure 并以内联 `CONFIG_SHELL/SHELL/TMPDIR` 覆盖，`env=conanbuild` 保留原有全部标志；make/install 统一携带可用 `SHELL/CONFIG_SHELL`；健康机零改动，上游测试口径不变 |
| 5 | 真机 compile 阶段 Signal 9、无 stdout/stderr（2026-09-24 预检） | HongMeng 内核对无 `.codesign` 的 ELF 直接 SIGKILL（backuppc-rsync/dascrubber/gtk 先例）；上游默认目标 `all->test` 会在构建后立即 exec 未签名的 `test/unittesttest`，表现为 compile 阶段 Signal 9 | 分两步构建：先以文件目标 `make lib/libunittest.a test/unittesttest`（不触发 test 配方的自动执行），经 `llvm-objcopy + binary-sign-tool -selfSign 1` 自签名（仅 OHOS，缺工具时降级警告，健康机零改动）后再显式运行；`package()` 安装前再签一次；test_package 的 `test_unittest` 同样先签名再执行；不改源码与测试口径 |
| 6 | 真机 compile 阶段 `make: *** No rule to make target 'lib/libunittest.a'. Stop.`（2026-09-24 预检，configure 成功后即错） | 上游为 2015 年手写 Makefile.in，顶层无 `lib/libunittest.a` 文件目标（`lib/` 默认目标才是 `libunittest.a`，`test/` 显式目标 `unittesttest` 才只链接不运行）；且配方在异地 `build-release` 内执行 configure/make，旧工程不支持 VPATH，构建目录下既无 `lib/` 产物路径也无对应显式规则 | 改为 in-source 子目录构建（emacs/zsv 同惯例）：configure 与 make/install 一律 `cwd=source_folder`；`lib/` 内 `make libunittest.a`（失败回退默认目标，同样不触发测试）+ `test/` 内 `make unittesttest`（只链接不运行），签名后再显式运行；`package()` 改为 `make install DESTDIR=<pkg>` 于源码根（`--prefix=/` 配合 DESTDIR）；不改源码与测试口径 |
| 7 | 真机 compile 阶段 `test/TestHolderTest.cpp:162 error: '~Helper' has a non-throwing exception specification but can still throw [-Werror,-Wexceptions]`（2026-09-24 预检，lib/ 已编过、test/ 编译中断） | 上游 `Makefile.utils.in` 写死 `-Wall -Werror`；`Helper` 析构故意 `throw std::runtime_error`（供 ExceptionOnTearDown 用例验证析构异常路径），新 clang 将其判为 `-Wexceptions` 错误；与问题 3 的 `auto_ptr` 弃用告警同类（皆为 2015 年代码 × 新编译器新增告警），但属不同告警分支，前次仅豁免 `deprecated-declarations` 未覆盖本分支 | 扩展同一最小豁免机制：`-Werror` 原地追加 `-Wno-error=exceptions`（与 `deprecated-declarations` 并列、逐词元幂等，configure 前后各一次）；其余 `-Werror` 保留，不改源码与测试口径；运行时语义待真机验证（若析构异常触发 terminate 则下轮加 `noexcept(false)` 源码补丁） |
| 8 | 真机上游测试 `TestHolderTest::ExceptionOnTearDown` abort：`libc++abi: terminating due to uncaught exception of type std::runtime_error: Helper destructor`，汇总 `68 passes and 1 failures`（2026-09-24 预检，编译已全过） | C++11 起析构函数隐式 `noexcept(true)`：`~Helper()` 无规格说明的 `throw` 在 OHOS libc++ 下直接 terminate，异常到不了 `ASSERT_EXCEPTION(holder.tearDown(), std::runtime_error)` 的 catch（C++03 下可捕获，属语言版本语义变迁，非 OHOS 缺信号/缺头文件）；另真机编译行证实 `-std=c++03` 未生效——上游 `Makefile.utils.in` 用 `$(CFLAGS)` 编译 `.cpp`，配方此前只写 `tc.cxxflags`，`@CFLAGS@` 内无 `-std`（与 Homebrew 把 `-std=c++03` 追加进 `CXX` 的做法背离） | 双改动（与前两轮 Werror/构建目录策略不同的新路线）：① conanfile 新增 `_hmbs_patch_testholder_noexcept()`（build() 内 configure 前调用，幂等）——对 `test/TestHolderTest.cpp` 的 `Helper` 析构做行级字符串替换，显式声明可抛（`__cplusplus>=201103L` 用 `noexcept(false)`，C++03 用 `throw(std::runtime_error)`；不断言改动、不跳过用例，只恢复“析构异常可被捕获”的原语义）；② `generate()` 内 `tc.cflags` 同步追加 `-std=c++03`（`Makefile.utils.in` 的编译与链接均用 `$(CFLAGS)`，双通道追加使文档声明与实际编译行一致，向 Homebrew 对齐）。注：首版曾用 conandata 补丁文件实现①，真机 `apply_conandata_patches` 报 `hunk no.1 doesn't match at line 148`（tarball 与 SVN trunk 视图行号不一致），故改用按实际内容定位的配方内替换；`manifest.yaml patches_applied` 保持空，PR 草稿同步更新。2026-09-24 下一轮真机证实有效：`Tests finished with 69 passes and 0 failures.` + `HMBS_UPSTREAM_TEST_RESULT passed (69/69)` |
| 9 | 真机 `package()` 阶段 `make install DESTDIR=<pkg>` 失败：`mkdir -p //share/unittest` → `Permission denied`，`make: *** [Makefile:31: install] Error 1`（2026-09-24 预检；此时上游测试已 69/69 通过） | 上一方案“`--prefix=/` 配合 `DESTDIR` 重定向”的假设无效：上游为 2015 年手写 `Makefile.in`，其 `install` 规则直写 `$(datadir)/unittest`（`--prefix=/` 下即 `//share/unittest`），根本不引用 `$(DESTDIR)`，故 `DESTDIR` 被静默忽略、安装直写主机根。与 shell/编译器/测试口径均无关，属安装期路径重定向机制误用 | 换路线，不再调用 `make install`（亦避开其 `install: test` 依赖重跑测试二进制）：`package()` 改为手动 `copy()` 与上游 install 等效的消费者子集（`lib/libunittest.a → lib/`、`include/*.hpp|*.tpp → include/unittest/`、`COPYING → licenses/`；`datadir` 下 docs 仅文档不影响链接）。不改源码、不动测试口径；消费者头布局（`<unittest/*.hpp>`）与 test_package 的 `find_package(unittest)` 预期一致 |
| 10 | 真机 test_package `generate()` 报错：`CMakeToolchain is declared in the generators attribute, but was instantiated in the generate() method too`（2026-09-24 预检；主包构建 + 上游 69/69 均已通过，`Package built` 后卡在消费者包生成） | conan 2.x 硬限制：同一 generator 只能声明一次。test_package 的 `generators` 属性含 `CMakeToolchain`，同时 `generate()` 内为做编译器回退又手动 `CMakeToolchain(self)` 并 `tc.generate()`，双重声明直接抛错。与编译器路径本身无关（主包的编译器回退逻辑正常，test_package 尚未走到编译器探测） | 只保留一处：`generators` 改为仅 `CMakeDeps`，`generate()` 内手动实例化保留（含编译器存在性回退逻辑不变）。上游/消费者测试口径不动 |
| 11 | 真机 test_package `build()` 编译失败：`test_unittest.cpp:124 error: unknown template name 'ExistingObject'` 及后续 5 处 `ExistingBase`/`existing()` 未声明（2026-09-24 预检；主包 + 上游 69/69 + test_package 生成均已通过） | 消费者测试自创用例的头文件缺失：`ExistingObject<>`/`ExistingBase<>` 模板定义在独立公共头 `include/ExistingBase.hpp`（上游 `UnitTest.hpp`/`Registry.hpp` 并不包含它），而 `test_unittest.cpp` 只包含了前两者。限定名 `UnitTest::ExistingObject` 本身正确（头文件内确为 `namespace UnitTest`），与命名空间无关；属测试代码引用遗漏，非配方打包缺头（`package()` 的 `*.hpp` 通配已覆盖该头） | 与之前配方/构建路线不同的测试代码修正：`test_unittest.cpp` 增加 `#include <unittest/ExistingBase.hpp>` 一行（用法对齐上游 `test/ExistingBaseTest.cpp`：被管类继承 `ExistingObject<T>` 计数、测试类继承 `ExistingBase<T>` 并用 `existing()` 查询）。不断言改动、不删用例，用例数仍为 8 |

## 依赖版本
- 无第三方依赖（纯标准 C++ 库 + POSIX 信号/`cxxabi`，均为工具链自带）
- 构建期：conan AutotoolsToolchain（OHOS profile `ci/conan/profiles/ohos-aarch64`）

## 验证结果
- 2026-09-24 真机预检：上游 `test/unittesttest` 已
  `Tests finished with 69 passes and 0 failures.`，
  `HMBS_UPSTREAM_TEST_RESULT={"status":"passed",...,"passed":69,...}`；
  同一轮随后卡在 `package()` 的 `make install`（`mkdir -p //share/unittest`
  Permission denied，见问题 9），test_package 尚未执行：
  - 上游 `test/unittesttest` 运行：69 passes / 0 failures（已实测）
  - `package()` 手动复制改写已提交待复检（含 `lib/libunittest.a`、
    `include/unittest/` 头布局）；2026-09-24 第二轮真机证实主包
    `Package '21b17f8b…' built` 通过，失败后移至 test_package
    `generate()` 的 CMakeToolchain 双重声明（见问题 10，已修复）；
    2026-09-24 第三轮真机证实 test_package 生成通过，失败后移至
    `build()` 的消费者测试缺头文件（见问题 11，已修复待复检）
  - test_package `test_unittest` 运行（期望 8 passes / 0 failures）：待复检
  - `HMBS_TEST_PACKAGE_RESULT` 标记行：待复检

```bash
# 预检将执行（hmbs 后台）：conan create archives/u/unittest/0.50-62
# 期望日志含：
#   Tests finished with 69 passes and 0 failures.
#   HMBS_UPSTREAM_TEST_RESULT={"status": "passed", ...}
#   Tests finished with 8 passes and 0 failures.
#   HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, ...}
```

## 交付物
- 配方：`archives/u/unittest/0.50-62/`（conanfile.py、conandata.yml、
  manifest.yaml、notes.md、test_package/）
- 软件级：`archives/u/unittest/manifest.yaml`、`archives/u/unittest/README.md`
- PR 草稿：`.hmbs/pr-body.md`（测试数字待真机 evidence 轮回填）

## 注意事项
- 本机为 Windows，`archives/g/gama` 上游存在非法文件名（`0002-...patch` 尾带
  `\r\r`），工作树以稀疏检出排除该目录 + `core.protectNTFS=false` 恢复；
  与本任务无关，保持不动，不纳入本 PR
- `archives/l/libXext` 与 `archives/l/libxext` 为上游大小写双目录，
  Windows 下同属一目录（基线现象），保持不动，不纳入本 PR
- 本轮未执行 `git commit`/`git push`/PR 创建；工作树保持未提交，
  由 HMBS 后台真机验证通过后统一提交
