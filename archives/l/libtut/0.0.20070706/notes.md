# libtut 0.0.20070706 适配笔记

## 基本信息

- 名称：libtut = TUT（Template Unit Tests），C++ 模板单元测试框架
  （作者 Vladimir Dyuzhev，tut.dozen.ru，项目已停更，2007-07-06 快照）
- 版本：0.0.20070706（Debian 日期版本，sid 至今仍为此版 -4）
- 许可：BSD-2-Clause（源 tarball 内无 LICENSE 文件，文本取自
  Debian 打包 debian/copyright；配方 license 字段如实标注）
- 语言/标准：C++98（现代编译器直接编译，无兼容性问题）
- 依赖：无（纯头文件）
- 交付形态：header-library，安装布局镜像 Debian libtut-dev：
  - `include/tut/tut.hpp`、`tut_reporter.hpp`、`tut_restartable.hpp`
  - 根级向后兼容壳 `include/tut.h`、`tut_reporter.h`、`tut_restartable.h`

## W0 依赖检查

无任何依赖（连可选依赖都没有），直接适配。

## 源码

- URL：`https://deb.debian.org/debian/pool/main/libt/libtut/libtut_0.0.20070706.orig.tar.gz`
- sha256：`2f1723afd49219a81706b96eef891ced53d43bbd7eed49ece51af1bf5f63d79d`
- md5：`883a9f66d8b073ef97490098d72eba72`（与 packages.debian.org 一致）
- 上游官方站（tut.dozen.ru、sourceforge 文件区）已消亡，Debian pool
  是该 tarball 的权威分发点。

## 上游结构

```
tut/                    3 个 .hpp（本体）
tut.h 等 3 个根级 .h     向后兼容壳（#include <tut/tut.hpp>）
selftest/               框架自带套件：21 个编译单元（main + 20 个运行组），
                        运行时注册 63 个套件用例；Makefile.gcc-unix:
                        g++ -ftemplate-depth-100 -I../tut -Wall -O2
examples/               basic / restartable / shared_ptr 三个示例
```

### 上游测试静态/运行口径对账（rule4 少报复核，2026-09-18 实测）

静态 `object::test<N>` 特化全量 126 处 = selftest 90 + examples 36；
审查脚本严格口径（无空格写法、无 testobject 前缀）计 **119** =
selftest 83 + examples 36。运行时注册执行的套件用例 **63**（真机
全绿）。对账：

| 构成 | 数量 | 说明 |
|------|------|------|
| selftest 套件用例（运行注册） | 63 | 20 个组全部执行，63/63 ok（真机） |
| selftest 内嵌辅助组/上限机制特化 | 27 | 不注册运行为套件用例（见下） |
| examples 演示特化 | 36 | 三个示例程序（basic 12 / restartable 12 / shared_ptr 12），用法演示非套件 |

27 个不注册特化的机制（读源+真机注册探针实证）：selftest 多个文件
为**双组结构**——外层组（如 "exceptions at test teardown time"）是
正式套件用例；另在外层数据结构内定义内嵌辅助 test_group 并以自定义
MaxTestsInGroup 上限实例化，专测注册/上限机制本身：

- `more_than_50.cpp`：`test_group<dummy,55>` 定义 `test<55>`，
  组名 "more than default 50 tests" 仅 1 用例注册运行；
- `less_than_50.cpp`：`test_group<dummy,2>` 定义 `test<3>`，
  验证超上限特化不注册；
- `teardown_ex.cpp`（12 静态/7 注册）、`callback.cpp`（8/6）、
  `ctor_ex.cpp`（5/3）、`runtime_exceptions.cpp`（7/3）、
  `set_test_name.cpp`（6/3）、`same_object_for_dummy.cpp`（3/1）、
  `constructed_instances.cpp`（3/1）、`setup_ex.cpp`（7/6）、
  `setup_new_copy.cpp`（2/1）、`runner.cpp`（4/3）同构。

书写变体：set_test_name.cpp 6 处空格写法（`test < N >`）与
bug_ensure_0_equals_0.cpp 的 `testobject::test<1>` 前缀不在审查
严格口径 83 内（宽松全量 90）。

真机注册探针：自写 main 链接 selftest 全部目标（排除上游 main.o），
逐组 run_test 枚举，20 组合计 63，与套件输出 ok:63 一致。

无 configure/CMake/Jam 实际构建需求（Jamfile 仅示例用），配方按
header-library 打包，不走上游构建系统（上游没有针对库本体的构建目标）。

## 可移植性评估（无需 patch）

- 头文件仅依赖 C++98 核心标准库；无平台 API。
- 唯一旧式语法：`throw()` 动态异常规范（C++17 前合法，clang 15 /
  gcc / MSVC 194 均接受，仅 -Wdeprecated 提示）。
- Windows SEH 分支在 `#if defined(TUT_USE_SEH)` 内，默认不启用，
  OHOS/Linux 无关。
- selftest 含 2007 年风格 `char* = "literal"`（C++11 起 deprecated），
  仅影响上游 selftest 编译告警，不影响本体头文件。

## 真机验证结果（2026-09-16，10.62.178.77，OHOS 6.0 / clang-15 / armv8 / libc++）

- `conan create . --profile:build=default --profile:host=ohos-aarch64-fixed`
  通过；package revision `fabf864275a967c32a5b9215103780d6` 与本机一致
  （header-library package_id 为空 settings 哈希）。
- test_package **10/10 PASS**（gnu17 / libc++），输出与本机完全一致。
- 上游 selftest **63/63 全绿**，`THIS VERSION OF TUT IS CORRECT`，exit 0。

两个真机实操要点：

1. profile 必须用 `ohos-aarch64-fixed`（含 `os.version=6.0` 与
   /data/service/hnp/bin 工具链路径）。裸 `ohos-aarch64` 缺 os.version，
   test_package 计算 package_id 时报
   `Invalid ID: 'settings.os.version' value not defined`。
2. selftest 必须以 `-std=gnu++98` 编译：teardown_ex 组故意从析构函数
   抛异常，C++11 起析构函数隐式 noexcept，默认标准（gnu17）下
   libc++abi 直接 `terminating due to uncaught exception`（Signal 6）。
   这是标准语义变更而非库缺陷——交付头文件在现代标准下正常
   （test_package gnu17 10/10 即证明）。
3. selftest 的 include 根是源码根目录 `-I$src`（测试用
   `<tut/tut.hpp>` 角括号形式），不是 `-I$src/tut`。

真机复现命令：

```sh
# 设备（10.62.178.77:2222）上，配方在 $HOME/tmp/libtut-recipe/0.0.20070706
cd $HOME/tmp/libtut-recipe/0.0.20070706
$HOME/.local/bin/conan create . --profile:build=default --profile:host=ohos-aarch64-fixed

# 上游 selftest（源码已在 conan cache）
src=/storage/Users/currentUser/.conan2/p/libtu6b6828de8a717/s/src
cd $src/selftest && for f in *.cpp; do \
  /data/service/hnp/bin/clang++ -std=gnu++98 -ftemplate-depth-100 \
  -I"$src" -Wall -O2 -c "$f" -o $HOME/tmp/libtut-selftest/"${f%.cpp}".o; done && \
  /data/service/hnp/bin/clang++ $HOME/tmp/libtut-selftest/*.o \
  -o $HOME/tmp/libtut-selftest/selftest && $HOME/tmp/libtut-selftest/selftest
# 预期：tests summary: ok:63 / THIS VERSION OF TUT IS CORRECT
```

## test_package 设计（两进制，10 + 22 断言）

`test_libtut`（框架语义验证，3 编译单元，覆盖 TUT 跨 TU 组注册这一
核心架构）：

- `group_core.cpp`：`<tut/tut.hpp>`，4 测试（3 ok + 1 故意 ensure 失败）
- `group_shim.cpp`：根壳 `<tut.h>`，2 测试（STL 容器 + tut::fail 抛
  tut::failure 且消息保留）
- `main.cpp`：定义 `tut::test_runner_singleton runner;`（每个应用恰好
  一处）；第一遍用官方 `tut::reporter` 跑全套件并断言
  `all_ok()==false`（恰有 1 个已知失败）；第二遍用自定义 counting
  callback 精确断言两组的 total/ok/fail/ex 计数；exit code 反映断言。

`test_consumer`（消费者用例，单文件双测试组）：用 TUT 驱动真实业务
模块——定容环形缓冲 + 滑动均值（FIFO 覆盖、size 封顶、滑动均值
ensure_distance、空访问 out_of_range 契约、零容量 invalid_argument）
与令牌累积器（append/join/clear）；6 个 TUT 用例内含 14 个 ensure
级断言 + 8 项驱动断言（reporter all_ok、两组注册与精确计数），全绿
退出码 0——展示库的预期用法（测别人的代码），与 test_libtut（测
TUT 自身语义，含故意失败）互补。

`test_ohos`（鸿蒙特有测试，`#ifdef __OHOS__` 编译守护）：

- OHOS 工具链下注册 "ohos platform characteristics" 组（3 用例）：
  `__OHOS__` 宏契约、uname machine 与编译期 `__aarch64__` 一致性、
  musl sysconf（`_SC_NPROCESSORS_CONF`/`_SC_PAGESIZE`）、HarmonyOS
  内核 utsname（`uname().sysname == "HarmonyOS"`，HM 内核特有）。
- main 另驱动 `tut_restartable.hpp`（第三个交付头，此前未覆盖）：
  journal.tut/log.tut 在 OHOS 文件系统的 ofstream/ifstream 持久化 +
  invoke_callback_ journal 重放（成功后 truncate 清空为完成标记），
  两轮运行均 3/3 ok。
- 非 OHOS 宿主（本地 MSVC 验证）：组被编译排除，驱动断言 0 组注册
  ——编译守护本身即被测契约的一部分。
- 设备实测事实依据：`__OHOS__=1`/`__aarch64__=1` 由 OHOS clang
  预定义（`-dM -E` 探测）；`uname -s` 返回 `HarmonyOS`；
  `__MUSL__`/`_LIBCPP_VERSION` 未定义故不断言。
- **tut_restartable 回调劫持陷阱（真机 SEGV 实证）**：
  `restartable_wrapper::invoke_callback_()` 会把 runner 的回调
  **永久替换**为 wrapper 的 callback 且从不恢复。回调对象必须
  存活到所有 wrapper 运行结束——若声明在块作用域，第二次
  wrapper 运行执行期第一个 `callback_->run_started()` 即调用已
  销毁对象 → Signal 11（log.tut 停留在 36B=test1、journal=0 是
  判别特征）。上游 examples 把 callback 放 main 顶层作用域即此
  因。test_ohos 的 rcb_run1/rcb_run2 提升到 main 作用域修复。

上游 selftest 与 test_package 互补：前者验证框架自身语义，
后者验证消费者视角的打包正确性（包含路径、跨 TU 注册）。

## 本机验证

- `conan create`（Windows MSVC 194 / cppstd 14）RC=0，
  test_package 10/10 PASS（见 reports/2026-09-16-device-validation.md）。
- MSVC 编译 2007 年头文件仅产生 C4290（throw()）类告警，无错误。

## shadow CI 待办

```sh
# 单包（worktree 内）
CI_PACKAGES="archives/l/libtut/0.0.20070706" zsh ci/conan/build_and_test.sh
```

## 下一步

- [x] 本机 conan create + test_package（test_libtut 10/10 + test_consumer 全过，MSVC 194）
- [x] 真机 conan create + test_libtut 10/10 + test_consumer 全过（OHOS 6.0 / clang-15 / gnu17）
- [x] 真机上游 selftest 63/63 全绿（-std=gnu++98）
- [x] 路径B知识草稿：E543（析构隐式 noexcept 语义变更）、E544（裸 profile 缺 os.version）
- [x] 消费者用例 test_consumer.cpp（环形缓冲 + 令牌累积器，双真机全绿）
- [ ] shadow CI 单包绿（L0/L1 pass，L5 确认 include/tut 真实存在）
- [x] 建 PR：`【知识库扩展】feat(libtut): 0.0.20070706 编译完成`
