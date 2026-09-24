# mathic 1.4 适配笔记

## 编译环境

- 构建系统：cmake（上游另有 autotools，本包只走 CMake）
- 编译日期：2026-09-24
- 编译器：clang/clang++（OHOS aarch64，libc++，C++17）
- 状态：built（待真机预检回填证据后由 HMBS 统一提交）
- 上游：https://github.com/Macaulay2/mathic（tag v1.4，2026-06-07）
- 源码：`https://github.com/Macaulay2/mathic/archive/refs/tags/v1.4.tar.gz`
- SHA256：`6af7df540751de13456ba6c21bf8d06f84d4c43cd2c8c2695ba4b820e2d72883`（108294 字节，已在本机下载验算）
- 许可证：LGPL-2.0-or-later（README 明示，见 lgpl-*.txt）

## 编译步骤

1. `generate()`：CMakeToolchain 钉 `BUILD_TESTING=ON`（上游 `if(BUILD_TESTING)`
   门控测试目标），`enable_pqsim/enable_divsim=OFF`；预置
   `MEMTAILOR_INCLUDE_DIR=<memtailor包>/include`、
   `MEMTAILOR_LIBRARIES=<memtailor包>/lib/libmemtailor.a` 命中上游
   `cmake/FindMemtailor.cmake`；CMakeDeps 生成 memtailor/gtest 配置。
2. `cmake.configure()` + `cmake.build()`：编译 `mathic` 静态库
   （13 个编译单元：Timer/ColumnPrinter/DivMask/Action/CliParser 等）。
3. `build()` 内全量实跑上游套件：`ctest -N` 取注册数（discovered），
   `ctest --output-on-failure` 实跑并逐行解析
   `Testing/Temporary/LastTest.log` 的 `Test #N ... Passed|Failed`
   （缺失时回退到 ctest stdout 同格式行，仅用其一），输出
   `HMBS_UPSTREAM_TEST_RESULT` 并落盘 `hmbs_upstream.json`。
4. `package()`：`cmake.install()` 装出 `include/mathic.h` +
   `include/mathic/*.h` + `lib/libmathic.a`；附加 `licenses/` 四文件；
   拷贝 `hmbs_upstream.json` 到 `res/` 供 test_package cache-hit 复发。
5. `test_package`：直接编译 `test_mathic.cpp`
  （`-I<mathic include> -I<memtailor include> -L... -lmathic -lmemtailor
   -pthread`），运行 6 组消费者断言，输出 `HMBS_TEST_PACKAGE_RESULT`
   并从 `res/hmbs_upstream.json` 复发上游标记。

## 上游测试盘点（gtest_macros=14）

| 文件 | TEST 宏 | 说明 |
|------|---------|------|
| `src/test/BitTriangle.cpp` | 3 | NoOp / emptyAndColumnCount / getSetBit |
| `src/test/DivFinder.cpp` | 1 | NoOp（KDTreeModel 除数查询桩） |
| `src/test/HashTable.cpp` | 2 | NoOp / StringKeys |
| `src/test/PairQueue.cpp` | 8 | RetirementSetToFalse/NoOp/emptyAndPairCount/Ordering/LargeIndices/ConDeconOfPairData/RetirementSetToTrue/Retirement |
| `src/test/testMain.cpp` | 0 | 仅 `main()`（InitGoogleTest + RUN_ALL_TESTS），不计入 |
| **合计** | **14** | 经 `gtest_discover_tests(... TEST_PREFIX unit-tests:)` 展开为 14 个 CTest 用例 |

四个测试 TU 通读无 `#if`/`#ifdef`/`#ifndef` 门控，无注释掉的 `TEST(`。
计数口径 `gtest_macros` 与 `ctest_entries` 在此包完全一致（discover 无过滤），
取 `gtest_macros` 为官方口径（与 memtailor 审计方式对齐）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `if(GTEST_FOUND)` 恒假 → configure 期 FetchContent git clone googletest 超时 | `find_package(GTest)` 走 CONFIG 模式（CMakeDeps）只设 `GTest_FOUND`；全大写 `GTEST_FOUND` 仅 MODULE 模式（FindGTest.cmake）设置 | patch 0002：判断改为 `GTest_FOUND OR GTEST_FOUND OR TARGET GTest::gtest`，以 target 存在性兜底 |
| 2 | `GTest::GTest` / `GTest::Main` target not found | 旧式别名仅 FindGTest.cmake 提供；Conan gtest/1.17.0.1 只声明 `GTest::gtest`/`gtest_main`/`gmock`/`gmock_main` | patch 0002：只链 `GTest::gtest`（不链 gtest_main：testMain.cpp 自带 main） |
| 3 | build 根目录 `ctest` 输出 `No tests were found!!!` 且退出码 0 | 上游 `include(CTest)` 写在 `src/CMakeLists.txt` 子目录，`enable_testing()` 仅对 `build/src/` 生效 | patch 0001：`include(CTest)` 提到顶层；`build()` 解析日志不只看退出码 |
| 4 | `lib/libmathic.a` 与 `include/mathic.h` 缺失 | `install(TARGETS mathic LIBRARY ...)` 仅声明 LIBRARY（静态库属 ARCHIVE）；伞头只挂 `PUBLIC_HEADER` 属性、无 DESTINATION | patch 0001：补 `ARCHIVE DESTINATION lib` 并 `install(FILES src/mathic.h DESTINATION include)` |
| 5 | `find_package(Memtailor REQUIRED)` 在 Conan 沙箱找不到包 | 上游 FindMemtailor 用 `find_path`/`find_library` 搜系统前缀 | `generate()` 预置 `MEMTAILOR_INCLUDE_DIR`/`MEMTAILOR_LIBRARIES` 缓存变量指向 memtailor 包目录，不改上游查找逻辑 |
| 6 | 消费者 `HashTable.h` 报 `memtailor.h: No such file` | mathic 公开头直接包含 memtailor 伞头，单 -I<mathic include> 不够 | test_package 同时 `-I<memtailor include>` 并链接 `-lmemtailor` |

## 真机预检轮次（2026-09-23，由 HMBS 后台执行）

- 第 1 轮：`def test_requires(self)` 方法定义被 Conan 2 拒绝加载
  （`Wrong 'test_requires' definition`）→ 已修：并入 `requirements()` 内
  调用 `self.test_requires()`（同 ezstream/bzrtp 先例），复检进入 configure。
- 第 2 轮：`cmake.configure()` 在顶层 `project()`（CMakeLists.txt:6）失败，
  `CMAKE_CXX_COMPILER: /data/service/hnp/bin/clang++` 后接编译器检测错误，
  伴 `System is unknown to cmake / Platform/HarmonyOS`（该提示本身仅警告，
  同构 memtailor/1.4 已合入且同名系统下通过）。判定为知识库 E191：
  HarmonyOS clang++ 默认链接配置在 try-compile 可执行探针期找不到
  libc++/libc++abi。对策：`generate()` 置
  `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`（E191 推荐做法；本包交付
  物为静态库无需链接，上游 14 用例测试可执行文件仍在 `cmake.build()` 真实
  链接并经 ctest 全量实跑，故不掩盖真实链接问题；同类先例
  adamstark-audiofile/1.1.4 带测试可执行文件亦如此）。
  同时 `build()` 对 `cmake.configure()` 加失败证据转储
  （`_dump_configure_evidence`：打印 `CMakeError.log`/`CMakeOutput.log`
  尾部与编译器版本后原样重抛，成功路径零影响），若 E191 假设不中，
  下轮日志将含真实错误而非截断摘要。`CMAKE_SYSTEM_NAME=Linux` 覆盖
  （E092）暂不采用：memtailor 同名系统已证明 HarmonyOS 名可配置，
  最小改动优先。
- 第 3 轮：E191 假设证伪——`STATIC_LIBRARY` 生效后（build 行号 351→402
  证明新代码已跑）`project()` 同位置复现失败，且 `clang --version` 探针
  正常（`Thread model: posix / InstalledDir: .../ohos-sdk.../llvm/bin`）。
  改走知识库 E557（草稿 E557-draft-1742，ls-hpack/2.3.5 PR #7487 实测）：
  病因为宿主工具链运行时缺失（OHOS clang 链接步 spawn 的 lld 系动态链接
  宿主 ELF，其 libxml2.so.16 经 RUNPATH 在当前宿主加载器下不可解析），
  CMake 只报表面症状。对策：① 撤销 `STATIC_LIBRARY` 绕过（E557 明令禁止，
  ayatana-indicator-keyboard 笔记亦拒绝采用）；② 主配方实现 E557 门控的
  C++ 版（`_get_cxx/_resolve_lld/_host_libdirs/_cxx_link_probe/
  _linker_runtime_environment`，与 ls-hpack 同算法：conf 优先→realpath→
  六类候选派生→只认实含 libxml2.so.16 的目录→ambient 真实编译+链接 probe→
  scoped 重试→Conan Environment 局部 prepend→fail closed），`build()` 的
  configure/build/ctest 全包在作用域内；③ configure 失败异常改带
  `CMakeError.log` 关键行（`_cmake_error_evidence`，bounded 1800 字符），
  保证预检摘要省略中间日志时下轮仍可见真实错误；④ test_package 实现等价
  最小门控（独立上下文，主配方作用域不传播）。ambient 健康时两处门控均
  返回 None，零行为变化。
- 第 4 轮（第 2 策略周期：E191 与 E557 同属“链接/宿主运行时”同一根因假设，
  连续两轮生效后同位置复现，均被证伪，本轮禁用该假设族）：重读原始日志与
  源码后确认——① 上游 `mathic/CMakeLists.txt` 在 `project()`（第 6 行）之前
  只有 `cmake_minimum_required` + `set(CXX_STANDARD 14)`，无任何 mathic 特有
  逻辑能干扰编译器检测；`find_package(Memtailor)` 等都在 `project()` 之后，
  不存在 mathic 特有的 project() 病因候选；② 同构 `memtailor/1.4` 以极简
  配方（plain `cmake.configure()`，无任何门控）在同一工具链/同一 profile 下
  已合入通过，是同环境可通过的直接反例；③ profile `ohos-aarch64` 本就全局
  导出 `llvm/lib` 的 `LD_LIBRARY_PATH`（正是 E557 要补的 libxml2.so.16 目录），
  配方级重复门控冗余，且门控的裸 flag probe（不带 toolchain 的 sysroot/target
  标志）无法复现 CMake 真实 try-compile 环境，误报后的 prepend 反而可能污染
  configure（E505 有 LD 劫持警告）；④ 前几轮 `_cmake_error_evidence` 只找
  `CMakeError.log`，而真机 cmake 4.4.3 的 configure 日志已搬到
  `CMakeFiles/<ver>/CMakeConfigureLog.yaml`，注定返回“no CMakeError.log”——
  这就是连续几轮看不见真实错误的原因。新路线（删除而非新增）：① 主配方与
  test_package 双双撤销 E557 门控（`_get_cxx/_resolve_lld/_host_libdirs/
  _cxx_link_probe/_linker_runtime_environment` 及 `Environment`/`contextlib`
  作用域），回到 memtailor 极简形态；② `_cmake_error_evidence` 改为 CMake 4
  全覆盖（CMakeConfigureLog.yaml→CMakeOutput.log→CMakeError.log→其它 *.log，
  缺失如实报告搜过位置，bounded 4000×2），下轮不再失明。补丁 0001/0002、
  上游测试与消费者测试逻辑保持不变。
- 第 5 轮（同一指纹第 2 次修复，换策略：上轮“撤销门控 + 取 yaml 尾部”已生效，
  新文案 `configure logs:` 与行号 431 证明新代码已跑，但同位置复现；且本轮
  输入的 yaml 片段是 benign 晚期事件——`addr2line` 查找结果与 PATH/
  INSTALL_PREFIX 变量转储，而非 CXX 编译器检测失败本身。结论：① 极简配方也
  失败，故障与配方复杂度无关，继续改配方形态已无意义；② 取文件尾部必然抓错
  事件。新策略只改证据“选择”：yaml 按 `  - kind:` 逐事件切分，按非零 exitCode/
  is not able/failed/error/找不到库/未定义引用打分，摘前 3 个失败事件的
  command/output 段（`_yaml_failed_events`），.log 文件保持关键行摘录。若下轮
  拿到的失败事件指向 SDK/工具链环境问题（如 lld 缺宿主库且 profile 路径漂移），
  则按守则停手报环境问题，不再改配方。
- 第 6 轮（同一指纹第 3 次修复：上轮行号 431→482 证明代码已跑，但 yaml 摘录与
  上轮一字不差仍是 addr2line benign 事件 → 定位到切分正则本身从未命中：yaml
  事件是 `  -` 独占一行、kind 在下一行，按 `  - kind:` 同行切分恒为 1 段而回退
  到尾部。修复：改按 `^  -` 行边界切分并兼容内联布局；双布局皆不命中时回退到
  全文失败行扫描而非尾部；摘录段扩展到 command/output/stdout/stderr/message，
  无标签事件取其尾部 2500 字符。三布局合成单测验证通过。）
- 第 7 轮（第 3 策略周期换路线）：前 3 轮只改 yaml 证据选择、同指纹 project()
  复现，证明故障与证据 plumbing 无关，改查工具链调用本身。配方新增只读探针
  `_probe_cxx_toolchain`（stat + --version + HMBS_* 回显），configure 前打印、
  失败时随异常携带；零 bypass、零门控。另纠正一次误判：曾按 GitHub raw
  v1.4 把 patch 0001 首 hunk 尾部改成 `add_compile_options(`，真机 tarball
  实测证明源码包 CMakeLists.txt 该处实为
  `add_library(memtailor STATIC IMPORTED)` + IMPORTED_LOCATION，原补丁上下文
  正确，本轮已恢复原状（raw 与 tarball 不一致，以 tarball 实测为准）。
- 第 8 轮（同指纹第 3 次修复：上轮探针首次生效，直接证实
  `/data/service/hnp/bin/clang/clang++` 双双 stat ENOENT，即 profile 旧路径在
  当前预检 worker 上缺失；这是 zydis/bzrtp 已验证的“真机 clang 迁移”模式）。
  改走已验证路线：主配方按工具分别解析真实编译器（conf 存在即用，否则
  PATH，否则 ~/usr/local/bin，不跨 C/CXX 回退），钉
  CMAKE_C/CXX_COMPILER，并对已生成的 conan_toolchain.cmake 做缺失时精确替换
  + build scope 导出 CC/CXX（zydis 实测仅钉 cache 未能覆盖烘焙旧值）；
  test_package 同理对 cxx 做存在性解析。旧路径有效时零改动，不跳过任何测试。

## 源码修改

- `patches/0001-CMakeLists.txt-toplevel-ctest-and-install-static.patch`（portability）
- `patches/0002-src-CMakeLists.txt-conan-gtest-targets.patch`（conan）
- 无 `__OHOS__` 平台宏（保持 POSIX 兼容，无需平台分支）。

## 依赖版本

- `memtailor/1.4`（requires，运行时；与 mathic 同一生峰版本）
- `gtest/1.17.0.1`（test_requires，仅测试；ohpcd 已发布）
- 工具链：clang 15 / libc++ / C++17（profile `ci/conan/profiles/ohos-aarch64`）

## 验证结果

- 本地（Windows 本机）：仅做配方静态检查（`python -m py_compile` 通过）与源码审计；
  不在本机运行 conan（按任务守则，编译验证在真机内执行）。
- 真机预检（HarmonyOS aarch64）：待 HMBS 后台执行，证据（`HMBS_UPSTREAM_TEST_RESULT`
  14 用例、`HMBS_TEST_PACKAGE_RESULT` 6 组）回填后以预检日志为准。
- 证伪预案：确认 `ctest.log` 与 `LastTest.log` 非空；`No tests were found`
  单独判失败；`100% tests passed` 汇总行仅作交叉验证，不参与计数。

- 第 9 轮：真机 compile 阶段 Signal 9，stdout/stderr 均空。串行构建 cmake.build(build_tool_args=["-j1"])封顶峰值压力，保持优化与测试不变。

- 第 10 轮：串行 -j1 后仍报 `/bin/sh: Out of memory`（compile 阶段，上游发现 0）。单进程 clang 编译模板+gtest 头即超限，并发封顶已无可压；patch 0003 仅把非交付物 `mathic-unit-tests` 封顶到 `-O1`（后出现的 `-O1` 覆盖 Release `-O3`），压住单进程峰值内存；测试源码与断言不变，交付的 `libmathic.a` 保持 Release 优化。串行 `-j1` 保留。

## 交付物

| 文件 | 说明 |
|------|------|
| `include/mathic.h` | 伞头文件（patch 0001 补装） |
| `include/mathic/*.h` | 模板头全集 |
| `lib/libmathic.a` | 静态库 |
| `licenses/` | lgpl-2.0/2.1/3.0 + README |
| `res/hmbs_upstream.json` | 上游证据（cache-hit 复发） |

## 注意事项

- 本包为纯库（`package_type=static-library`），无 `commands.json`（R38 仅 tool 需要）。
- 库名 `mathic` 与 OHOS 系统库无同名冲突，无需 R26 特殊处理（默认静态已满足）。
- `package_info.requires = ["memtailor::memtailor"]` 已声明，CMake 消费者传递正确。
- `pqsim`/`divsim` 仿真程序默认关闭（`enable_pqsim/enable_divsim=OFF`），保持产物纯粹。

- 第 11 轮：真机 source() 期 `Failed to parse patch: 0003-test-O1-cap-compile-memory.patch`（`extra lines for hunk no.1 at 17`）。根因为 hunk 头 `@@ -63,7 +63,13 @@` 计数错误：body 实际 old=7（6 行上下文+尾部 endif）/new=15（7 上下文+8 行新增），头写 13 致解析器判多余行；起始行 63 亦与上游实际 75（0002 后 80）不符。修复：头改为 `@@ -80,7 +80,15 @@`（0002 后行号，old=7/new=15 与 body 一致，已做 hunk 计数自检）。测试源码与 -O1 策略不变。
- 第 12 轮：补丁生效后编译通过（libmathic.a 产出），但上游 14 发现/0 执行。根因为计数源选错：`LastTest.log` 为多行格式（`Test #N:` 与 `Test Passed.` 分处两行），用同行正则 `Test\s+#\d+[^\n]*?\b(Passed|Failed)` 逐行解析恒得 0（本地复现：LastTest.log 样例计数 0/0，stdout 样例 2/0）；且仅当文件缺失才回退 stdout，文件存在时永不回退。修复：executed/passed/failed 唯一来源改为当次 `ctest --output-on-failure` stdout 单行结果；LastTest.log 仅记存在性作证据；汇总行搜前先剥 ANSI（liblzf 先例软校验适配，仍仅交叉验证）。单源、无减法推导，恒等式自检保留。
- 第 13 轮：计数源切 stdout 后推进到 5/14（5 通过、0 失败、9 未执行，无汇总行）。仍有 9 个无结果行，疑为崩溃态（`***Exception`）被旧正则漏计为跳过，且缺失用例名与 ctest 返回码未进证据，下轮无法定位。修复（与前两轮不同策略，不动计数源）：结果行新增 `Exception` 判失败；`ctest -N` 留存注册名、stdout 留存执行名，gaps 与异常均携带未执行用例名（前 8）+ ctest_rc + tail 摘录；记录 ctest returncode 区分正常退出与 SIGKILL/OOM 中断。单源逐行解析不变。
- 第 14 轮（第 4 策略周期换路线：上轮“崩溃态 Exception”假设被本轮日志证伪——ctest_rc=0 且 tail 明确 `100% tests passed out of 14`，14 个用例全部通过，无崩溃/中断；故故障不在被测程序而在计数器本身）：重读日志发现 executed=5 恰为双位数用例数（10-14），而 tail 中 5/14-9/14 同样 Passed 却被记为未执行，且未执行名单恰为 1-9。根因为 `if "Test #" not in line` 单空格字面量预过滤——ctest 为对齐个位数用双空格 `Test  #5:`，十位数才用单空格 `Test #10:`，1-9 恒被丢弃。修复（不动计数源、不动正则语义）：删除该脆弱预过滤，直接用 `_TEST_LINE.search(line)` 逐行判定（该正则已用 `Test\s+#\d+` 兼容一/双空格）；测试源码与断言不变。
