# boost1.84-type_erasure 1.84.0 编译笔记

## 任务背景

- **任务**：积分赛 — boost 1.84 组件拆分包（type_erasure）
- **申请人**：momimgya
- **队伍**：干
- **平台分支**：feat/boost1.84-type_erasure-1.84.0
- **底稿**：仓库 main 的 archives/b/boost/1.84.0/（元包）与同系列拆分包
  （boost1.84-coroutine / program_options / iostreams / contract）
- **开始时间**：2026-09-08

## 形态选型

独立裁剪包（非 requires 元包），与同系列 boost1.84-program_options /
iostreams / coroutine 拆分包对齐。原因：

1. 组件拆分任务要求独立包，版本演进不与元包修订锁死（R37）；
2. 元包与组件包若同用 cmake_file_name "Boost"，同一工程共存时
   CMakeDeps 生成文件互相覆盖会冲突；本包 cmake_file_name 用包名
   `boost1.84-type_erasure`（同 atomic/log/wave/iostreams 先例）；
3. 全量 boost 头随包安装，下游无需再装 boost/1.84.0 元包
   （同 iostreams/coroutine 自包含模式）。

库形态：static-library。libboost_type_erasure 无 OHOS 系统同名库，
R26 无静态强制要求，但保持与系列一致的静态归档形态。

## W0 依赖检查（R36）

- 本包 `requirements()` 为空：type_erasure 编译库仅依赖 boost 头自身
  （dynamic_binding.cpp 用 Boost.Thread 头的 shared_mutex，头-only 用法，
  `-pthread` 即可，无需 libboost_thread）+ 系统 libc；
- zlib/bzip2 等压缩后端与本包无关（iostreams 专属）；
- 结论：无外部 conan 依赖，无需先发布依赖包。

## 上游源码审计

- 上游仓库：https://github.com/boostorg/type_erasure（tag boost-1.84.0）；
- 发行 tarball 与元包同源：boost_1_84_0.tar.gz，sha256
  `a5800f405508f5df8114558ca9855d2640a2de8f0445f051fa1c7c3383045724`；
- 编译库源码：`libs/type_erasure/src/dynamic_binding.cpp`（全库唯一 TU，
  动态绑定注册表；文件头自带 `#define BOOST_TYPE_ERASURE_SOURCE`）；
- 上游测试：`libs/type_erasure/test/`，以 `test/Jamfile.jam` 为权威清单：
  run 31 + compile 5 + compile-fail 24 = 60 个目标（详见
  test_package/MANIFEST.yml 逐项清单）；
- 测试框架：boost.test（run 型）；compile/compile-fail 型为纯编译期正负向测试。

## 关键实验记录（待真机预检回填实测结果）

### 实验设计 1：编译库手动归档（绕过 b2，E068）

```bash
clang++ -std=c++17 -stdlib=libc++ -pthread -fPIC -O2 -DNDEBUG \
  -DBOOST_ALL_NO_LIB -DBOOST_TYPE_ERASURE_NO_LIB \
  -DBOOST_TYPE_ERASURE_STATIC_LINK \
  -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE \
  -I<boost_root> -c libs/type_erasure/src/dynamic_binding.cpp -o dynamic_binding.o
llvm-ar rcs libboost_type_erasure.a dynamic_binding.o
```

### 实验设计 2：上游测试全量驱动（60 项，绕过 b2）

- run 31：将 `#include <boost/test/unit_test.hpp>` 改写为
  `#include <boost/test/included/unit_test.hpp>`（单头全实现，与
  boost1.84-coroutine 同款技巧），`-DBOOST_TEST_NO_LIB`，编译后直接运行，
  退出码 0 判通过；仅 test_dynamic_any_cast 额外链接
  `-lboost_type_erasure`；
- compile 5：`-fsyntax-only`，成功为通过；
- compile-fail 24：`-fsyntax-only`，失败为通过（负向测试）；
- test_assign 含上游 gcc/windows 专用变体要求，在 OHOS clang 下按常规
  run 执行；test_limits 需 C++11 右值引用/模板别名/变长模板，
  clang15 + C++17 满足。

### 实验设计 3：test_package 消费者测试设计

覆盖 4 个能力面（10 个断言）：异构 printable any（流式输出 + any_cast
回取）、擦除 callable（lambda 与含状态仿函数）、擦除成员函数
（BOOST_TYPE_ERASURE_MEMBER）、动态绑定注册与跨 concept 视图转换
（register_binding + binding，链接 libboost_type_erasure 验证编译库可用）。

注意点：

- 测试二进制加 `-static-libstdc++`（conanrun 环境无 SDK 的
  libc++_shared.so 搜索路径，动态链接会 rc=127）；
- `no_copy_source = True`：boost 源码树 5 万+文件，HMDFS 上整体复制极慢，
  配方只读源码，直接在 source_folder 上编译（同 iostreams 先例）；
- 上游 run 测试改写在 build_folder 下的 upstream_test_patched/ 副本上进行，
  不污染源码树。

## 已知平台限制

- OHOS musl 无 pthread_setcancelstate：复用底稿已验证补丁
  （BOOST_SP_NO_PTHREAD_SETCANCELSTATE 特性检测宏守卫，R8 合规，
  非平台宏），headers 组件同时向消费者传播该宏；
- b2 构建系统在 OHOS 不兼容（E068），全程手动编译驱动。
- 上游 build/Jamfile.v2 把 libboost_type_erasure 链接到 /boost//thread
  （dynamic_binding.cpp 用 boost::shared_mutex）；OHOS 无 thread 拆分包，
  真机预检 test_dynamic_any_cast 链接失败（undefined symbol:
  boost::this_thread::disable_interruption 等，59/60）。本轮新增
  patches/0002，用 C++17 std::shared_mutex/unique_lock/shared_lock 替换
  进程内注册表读写锁（语义相同，无已发布 ABI 影响），消除对编译型
  Boost.Thread 的依赖；type_erasure 组件声明 system_libs pthread，
  test_package 显式链接 Threads::Threads。

## 配方结构

- `requirements`: 无（仅 boost 头自身 + libc）；
- `build()`: apply patch → 编译归档 libboost_type_erasure.a →
  全量运行 60 项上游测试并落盘 upstream-tests-report.txt +
  upstream_test_result.json，同时打印 HMBS_UPSTREAM_TEST_RESULT 行；
- `package()`: 全量 boost/* 头 + libboost_type_erasure.a +
  res/upstream_test_result.json（供 test_package 重发上游证据）；
- `package_info()`: cmake_file_name `boost1.84-type_erasure`，headers 组件
  （defines 传播）+ type_erasure 组件（libs 声明）。

## 结论（待真机预检后确认）

type_erasure 组件在 HarmonyOS PC 上的可用性结论，以真机预检日志为准，
本轮不预断。

---

**编写**: 2026-09-08
**最终状态**: 待真机预检（未提交）

## 真机预检反馈（2026-09-08 第五轮）与修复

- 现象：test_package 直连 clang++ 编译失败，首错
  `vtable.hpp:143 static_cast ... vtable_storage<...has_bump...> to
  vtable_entry<typeid_> ... not related`，实例化链
  `binding.hpp:210 lookup<typeid_>` ← `any_cast<counter>(x)`
  （test_boost_type_erasure.cpp:72）。
- 根因：`bumper` 概念仅含 `copy_constructible + has_bump`，
  缺 `typeid_<>`；而 `any_cast` 需经 `typeid_` vtable 表项取回
  具体类型，无该表项即 static_cast 非法。属测试概念声明遗漏，
  非上游/工具链问题。
- 修复（仅 test_package/test_boost_type_erasure.cpp，口径不变）：
  `bumper` 增加 `typeid_<>`（与 printable/concept_a/concept_b
  一致）；断言数量、覆盖能力面、链接库均不变。
  readonly_tmp 系 preflight.sh 自身 /tmp 告警，配方/test_package
  已复用 HMBS TMPDIR，本轮不另改。待下轮真机预检验证。

## 真机预检反馈（2026-09-08 第四轮）与修复

- 现象：test_package 直连 clang++ 编译失败 7 errors。首错
  `test_boost_type_erasure.cpp:83 expected '>'`（`relaxed<>` 处）；
  后续 `binding<concept_a>()` 触发
  `BOOST_MPL_ASSERT(is_relaxed<Concept>)`，以及 vtable 级联报错。
- 根因：`boost::type_erasure::relaxed` 是普通 struct（`vector0<>`
  子类，见 relaxed.hpp），不是模板，`relaxed<>` 非法；且
  `binding<Concept>` 默认构造要求 Concept 含 relaxed，而原
  concept_a 无 relaxed；另原 `register_binding<concept_a, concept_b>()`
  把概念向量当具体类型注册（正确重载是
  `register_binding<Concept, T>`，T 为具体模型类型，见
  register_binding.hpp），属误用。
- 修复（仅 test_package/test_boost_type_erasure.cpp，口径不变）：
  concept_b 改为 `relaxed`（无 `<>`）；第 4 节改用上游
  test_dynamic_any_cast.cpp 同款 `register_binding<Concept, std::string>()`
  + `dynamic_any_cast` 跨概念视图转换（同时验证
  libboost_type_erasure 注册表链接可用），不再使用
  `binding<concept_a>()` 默认构造。断言数量与覆盖面不变。
  待下轮真机预检验证。

## 真机预检反馈（2026-09-08 第三轮）与修复

- 上轮直连策略生效：CMake 已消失，真机直接执行了 clang++ 编译消费者
  测试（编译器取 PATH 首个 harmonybrew clang++，驱动正常）。新失败具体
  可定位：`test_boost_type_erasure.cpp:22: 'boost/type_erasure/
  ostreamable.hpp' file not found`——该头上游不存在（复核：上游
  test_stream.cpp 用 operators.hpp；包内 `copy boost/*` 全量拷贝不可能
  单漏一个文件），`ostreamable<>` 概念在 `operators.hpp` 中定义。
- 修复（仅测试源码，不改口径）：`ostreamable.hpp` 改为
  `operators.hpp`；另显式加 `relaxed.hpp`（concept_b 用到的
  `relaxed<>` 所在的上游头，有 include guard，冗余则无害）。断言数量、
  覆盖能力面、链接库均不变。主配方自第一轮未变，上轮 60/60 仍有效；
  本轮主包预计再次缓存命中，上游证据由 test_package 从包内 res/ 重发。
  待下轮真机预检验证。

## 真机预检反馈（2026-09-08 第二轮）与换策略修复

- 上轮修复（test_package 注入 CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY）
  已同步生效（失败行号 54→72），但 CMake 报完全相同的
  `project()` 编译器检查失败。STATIC_LIBRARY 已无链接步骤仍同错，
  证伪 E191“链接失败”假说；合同包（纯工具链）能过而本包两次卡死，
  CMake 缓存/工具链变量路径亦不可靠。
- 新策略（与上轮不同）：test_package 去 CMake 化，改直连 clang++ 编译
  + 运行。依据：docs/ADAPTATION_GUIDE.md §5 test_package 模板即直连
  `clang test.c -o test` 写法；已合入的 baitfisher test_package 无 CMake、
  直接取 `tools.build:compiler_executables` 编译运行；本配方 60 项上游
  测试在真机全部是手动 clang++ 编译运行通过的，可复用同款 flags。
- 改动（仅 test_package/conanfile.py）：删除 generators/CMakeToolchain/
  layout，build() 用 conf 解析的 clang++ 直连编译
  test_boost_type_erasure.cpp（-std=c++17 -stdlib=libc++ -pthread，
  包 defines 全带，链接包内 libboost_type_erasure.a，
  -static-libstdc++，产物名不变）；test() 直接运行二进制并沿用原
  HMBS 双标记逻辑（discovered=1；上游证据沿用包内 res/ 重发，主配方
  自上轮未变故上轮 60/60 实测仍有效）。测试源码/断言/链接库/口径不变，
  CMakeLists.txt 留作 CMake 消费者示例。待下轮真机预检验证。

## 真机预检反馈（2026-09-08 第一轮）与修复（已证伪，见第二轮）

- 现象：配方 build() 中上游 60/60 通过、lib 归档成功；test_package 的
  `cmake.configure()` 在 `CMakeLists.txt:2 (project)` 失败，CMake 报
  `CMAKE_CXX_COMPILER (/data/service/hnp/bin/clang++) is not able to
  compile a simple test program`。
- 根因：E191 —— OHOS clang 默认链接配置找不到 libc++/libc++abi，
  try-compile 可执行文件链接失败；编译器本身正常（配方内全部手动
  clang++ 调用成功）。非 E455（profile 已是 libc++，无 libstdc++
  证据）、非 E346（真机实内核，且 31 个 run 二进制已正常执行）。
- 修复（仅 test_package/conanfile.py）：CMakeDeps 改显式
  `generate()`，注入
  `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`（与已合入的
  observer-ptr-lite/0.4.0 同款），try-compile 只编译归档、不链接可执行
  文件；另显式 `CMAKE_CXX_STANDARD=17/REQUIRED`（与已合入的同系列
  boost1.84-contract/1.84.0 对齐）；build()/test() 同步导出
  HMBS_TMPDIR（readonly_tmp 加固）。CMakeLists/测试源码/配方主体未动，
  测试口径不变。待下轮真机预检验证。
