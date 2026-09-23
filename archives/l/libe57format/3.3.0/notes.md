# libe57format 3.3.0 适配笔记

## 概述

libe57format (上游 asmaloney/libE57Format, v3.3.0, 2025-10-24) 是 E57
三维点云文件格式的读写库, 提供 Simple API (读写扫描点云) 与
Foundation API。C++14, CMake >= 3.15 构建, XML 解析依赖 Xerces-C 3.2。
本适配默认构建静态库, 与 ConanCenter 同策略。

## 编译环境

- 构建系统: cmake
- 编译器: clang/clang++ (HarmonyOS PC aarch64, libc++)
- 状态: built (配方已完成, 待真机预检实测后由 HMBS 统一提交)

## 上游测试清点 (源码审计, 非运行结果)

- 位置: 上游 `test/src/*.cpp` (GoogleTest 框架)
- 总数: 43 个 `TEST` / 8 个测试套件
  - `test_SimpleData.cpp`: 6 个 (SimpleDataHeader 5 + SimpleData 1)
  - `test_SimpleReader.cpp`: 14 个 (SimpleReader 1 + SimpleReaderData 13)
  - `test_SimpleWriter.cpp`: 16 个 (SimpleWriter 15 + SimpleWriterData 1)
  - `test_StringFunctions.cpp`: 6 个 (仅静态库构建时编译)
  - `TestData.cpp`: 1 个 (测试数据仓存在性断言)
- 运行入口: `test/testE57` 二进制 (上游未注册 `add_test`, 配方补加后以
  单个 CTest 用例 `testE57` 驱动, `ctest --output-on-failure --verbose`)
- 数据依赖: `*Data` 套件 (15 个: SimpleReaderData 13 + SimpleWriterData 1
  + TestData 1) 需官方测试数据仓
  (asmaloney/libE57Format-test-data, 约 1 MB); 缺数据时上游 `main()`
  自动过滤, 不失败。
- 执行数与通过率以真机预检日志为准, 见 PR 正文。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `test/CMakeLists.txt` 要求 `test/extern/googletest` 子模块, tarball 中为空目录, configure 直接 FATAL_ERROR | 上游用 git submodule 拉 googletest, release 包不含 | 配方 `test_requires("gtest/1.17.0.1")`, 在 `_patch_sources` 中把 `add_subdirectory(extern/googletest)` 换成 `find_package(GTest REQUIRED)` 并链接 `GTest::gtest_main` |
| 2 | GTest 1.17 头文件要求 C++17, 上游测试目标指定 `cxx_std_14` | 依赖版本高于上游编写时的基线 | 仅测试目标提至 `cxx_std_17`, 库本身保持 C++14 (与上游一致) |
| 3 | 上游测试无条件 `enable_all_sanitizers(testE57)` (ASan+UBSan) | OHOS NDK sysroot 无 sanitizer 运行时, 链接/运行失败 | 在配方中删除该调用并注明原因 |
| 4 | 上游测试未调用 `add_test`, `ctest` 报 "No tests were found" | 上游只支持直接运行 `./test/testE57` | 配方在替换点追加 `add_test(NAME testE57 COMMAND testE57)`, 使 `cmake.test()` 真实驱动 |
| 5 | 链接 `XercesC::XercesC` 找不到目标 | 本仓 xerces-c 包导出的是小写目标 `xerces-c::xerces-c` | 替换为小写目标名 |
| 6 | `*Data` 套件需外部数据, 真机/CI 无预置 | 上游数据在独立仓库 | `source()` 中随源码拉取官方数据仓 (sha256 钉住), 并透过 `E57_TEST_DATA_PATH` 告知上游构建 |
| 7 | 真机 `conan create` 在依赖图阶段报 `xerces-c/3.2.5: Invalid: Option 'network_accessor=socket' is only supported on ('Linux', ...)` | 依赖解析到 ConanCenter 版 xerces-c, 其 `validate()` 把 `network_accessor=socket` 限死在 Linux/Mac/Android 等系统, OHOS 直接判 Invalid | 配方 `configure()` 中按需关闭该选项 (`self.options["xerces-c"].network = False`, E57 只做本地 XML 解析、无需网络; 本仓 xerces-c 无此选项时 try/except 跳过)。同时 `_patch_sources` 中 `XercesC::XercesC` 大小写替换改为按实际解析到的配方条件执行 (本仓小写目标才替换, ConanCenter 上游拼写保持不动) |
| 8 | 上轮修复后校验通过, 真机转而从源码构建 `xerces-c` (ConanCenter 修订版), 其自身 `build()` 内 `cmake.configure()` 在上游 `CMakeLists.txt:58 project()` 处报 `CMAKE_C_COMPILER` / `CMAKE_CXX_COMPILER` 错误 (`ERROR: xerces-c/3.2.5: Error in build() method, line 156`) | 逐行核对确认报错行号 156 恰为 ConanCenter 版 xerces-c 配方的 `cmake.configure()` (本仓配方全文件不足 120 行, 不可能报 156 行), 即失败发生在依赖自身的构建内。conan 无 `--update` 时按 remote 顺序取首个命中的修订版, 预检先查 conancenter 故命中 CCI 修订版 (首轮日志为证); 二进制与修订版绑定, ohpcd 上本仓修订版的已发布二进制无法复用, 只能从源码构建。`project()` 之前无任何配方可控的 CMake 逻辑介入, 且同 profile 下任何 CMake 包生成的工具链中编译器检测输入完全一致, 本配方无法从外部影响依赖的构建。CI 的 `ci/conan/setup.sh` 明确禁用 conancenter、只用 ohpcd, 故走本仓修订版, 与预检路径不一致 | 本轮未改动任何构建逻辑: 编译器检测失败的确切 stderr 在聚焦摘要中被省略, 盲改工具链变量无法验证且作用不到依赖构建。诊断记入本表; 需后端提供完整 CMake 错误文本 (含 `project()` 下被省略的编译器输出) 或调整预检 remote 顺序 (与 CI 一致优先 ohpcd) 后再定下一步 |
| 9 | 上轮 `network=False` 后校验通过, 但真机仍选中 CCI 修订版 xerces-c 并在其自身 `build()` 的 `project()` 编译器检测处失败 (ERROR 行号 156 = CCI 配方, 本仓配方不足 120 行); 依赖构建发生在消费者 `generate()` 之前, 消费者侧任何选项/工具链设置都作用不到 | 上一方案 (`configure()` 关选项 + 目标名条件替换) 只解决“选中 CCI 后的容忍”, 不改变修订版选择 (解析先于选项应用); 且“等后端调 remote 顺序”在配方外, 两轮复跑仍命中 CCI, 证明容忍路线已耗尽。改换 atracdenc/libgsf 已验证路线: 裸版本引用在双 remote 下有歧义是配方缺陷, 必须在配方内用 RREV 显式 pin 到已适配修订版 | `requirements()` 改为 `xerces-c/3.2.5#9086fe3ffea711440f8f71d66d6ca6d0`, `test_requires()` 改为 `gtest/1.17.0.1#9ffddd9d9fcc4049457a71bc4b81d2ee`; RREV 取自 ohpcd conan v2 revisions API 实测 (2026-09-14, 各仅一个 revision), 非本地复算。pin 后解析到本仓配方+已发布二进制, 跳过 CCI 源码构建; 原 `configure()` 关选项块降为兜底 no-op (本仓修订版无此选项), `_patch_sources` 的大小写条件替换保持自适应 (pin 下恒走小写分支, 正确) |
| 10 | RREV pin 后依赖解析已正常 (日志出现小写 `xerces-c::xerces-c`, 无 xerces 构建错误), 但本包自身 `build()` 的 `cmake.configure()` 在上游 `CMakeLists.txt:38 project()` (CXX-only) 处报 `CMAKE_CXX_COMPILER` 错误 (ERROR 行号 161 = 本配方)。复盘: 上轮 CCI xerces 与本轮本包是**同一签名** (不同配方/不同上游, 同一 `project()` 编译器检测失败 + `System is unknown to cmake`), 与配方内容无关, 真正共因是 E092 (CMake 无 Platform/HarmonyOS 模块) 下 HarmonyOS 映射在真机 cmake 4.4.3 上过不了编译器检测；RREV 只决定“谁先撞墙”，修不了墙本身 | 改换已合入先例路线 (zxc/ableton-link/function2, 2026-06-30/08-13/08-31 合入): `generate()` 中 `tc.variables["CMAKE_SYSTEM_NAME"]="Linux"` + `CMAKE_SYSTEM_PROCESSOR="aarch64"`。审计上游顶层 CMakeLists (v3.3.0 原文): 无任何 CMAKE_SYSTEM_NAME/LINUX 门控分支, 覆盖对上游零行为影响, 只修复 cmake 自身平台机制；默认静态构建, 无 SONAME 顾虑。test_package 同步改显式 `generate()` 加同样两行 (其 CMakeLists 仅两个 CXX 可执行文件, 无平台分支)。`readonly_tmp` 系 preflight.sh 自身 noise (atracdenc 同结论), 配方与上游均无 /tmp 硬编码, 未处理 |
| 11 | Linux 覆盖已生效 (本轮无 `System is unknown` 警告, 错误行号 161→172 恰为上轮新增 11 行所致) 但 `project()` 仍失败并新增 `-- The CXX compiler identification is unknown`: 编译器识别本身过不了, 与平台模块无关。复盘三轮: 容忍 CCI (RREV pin 有效但只解决依赖选择) → Linux 覆盖 (ddate 配方文档明示试过同样路线仍红, critnib 亦证实 Linux-override + 可写 TMPDIR 下仍是同一 ID 失败) 均触及 CMake 自身探测天花板；机制层面见 E557 (OHOS clang 链接步 spawn 的 lld 因宿主 .so 如 libxml2.so.16 无法解析而死亡, CMake 只报探测失败；profile 注释亦记载同一 lld 缺库问题) | 改换 09-10/09-11 刚合入的直编路线 (clamav-libunrar/critnib, 同签名同 worker): 主配方与 test_package 不再执行任何 CMake `project()`，直接用 conf 配置的 clang++ 编译：库取上游 src/CMakeLists.txt 的精确 42 个 .cpp (C++14/-fPIC/上游等价 defines 与 -I)，静态经 llvm-ar (shared 走 -shared + 上游 SONAME + 兼容签名, 仿 clamav)，E57Export.h 按 GenerateExportHeader 静态/共享语义现场生成并随包安装；上游测试编译 test/src 精确源集 (C++17 供 GTest 1.17，TEST_DATA_PATH 取与 find_path 等价值，只链接 gtest 因上游自带 main)，`--gtest_list_tests` 先计数再实跑并解析 `ran/PASSED` 行输出 `framework=gtest` 标记 (fail-closed：计数为 0 或解析失败直接抛错)；test_package 同理直编直跑。构建前导出可写 TMPDIR (E002, 仿 clamav) 并先跑 trivial 编译链接 smoke (仿 critnib，工具链真坏时输出真实 stderr)。跳过 sanitizer/LTO/ccache/告警旗 (OHOS 无 ASan 运行时；仅影响优化与告警, 不改变语义) |
| 12 | 直编后编译链接全绿, 上游测试 `discovered=43` 但 `executed=0/passed=0` 致 `ConanException: upstream tests failed`, HMBS 附带 `readonly_tmp` 诊断。核查: 上游 `test/src/test_SimpleWriter.cpp` 等全部写 `./*.e57` 相对路径, 无 `/tmp` 硬编码 (源码实证); `/tmp` 报错仅来自 `preflight.sh` 自身 (`can't create temporary file /tmp/...: Read-only file system`, 详见本轮真机摘要头部, atracdenc 同款 noise)。另配方 `_run_gtest` 有两处解析缺陷: ① `passed == ran` 要求满分, 而 OHOS 缺 `fr_FR` locale 导致 `StringFunctions.FloatToStrLocale` 合法 `GTEST_SKIP` (日志实证), 42/43 即被判 fail; ② 汇总正则未做 ANSI 脱色, 上游 `main.cpp` 强制 `FLAGS_gtest_color=yes`, 彩色输出可使 `ran` 解析为 0 | 仅改测试接线, 零改动用例断言: `_run_gtest` 传 `--gtest_color=no` (仅输出格式, `InitGoogleTest` 后解析覆盖 `main.cpp` 的 `yes`, 语义零影响) + 解析前脱 ANSI; 状态判据改为 `passed + skipped == ran` (skip 计为跳过不计失败); 汇总缺失时回退计数带 `(N ms)` 的逐用例 `OK/FAILED/SKIPPED` 行 (防 `executed=0` 误报, 上限 `discovered`); `_gtest_discovered`/`_run_gtest` 均显式透传可写 `TMPDIR/TMP/TEMP` (只换临时根目录, 不删测试)。上游确无 `/tmp` 硬编码故不做源码替换 |
| 13 | 直编全绿但 `discovered=43/executed=43/passed=42/skipped=1` 被判 `incomplete (upstream_test)`: 唯一跳过是 `StringFunctions.FloatToStrLocale`，`fr_FR locale not available: collate_byname failed`（真机 gtest 实证）。`floatingPointToStr` 内部已 `imbue(classic)`，缺的只是证明“全局法语环境下仍输出 `.`”所需的 OS locale 数据库；musl/OHOS 无 localedef 数据库，装 locale 不可行 | 测试接线不动（不断言删除、不静默跳过）：新增 `patches/0001-test-StringFunctions-locale-fallback.patch`（`portability`，`conandata.yml` 登记，`apply_conandata_patches` 在 `build()` 首行应用），仅改该 TEST 的 locale 获取：先试 `fr_FR`/`fr_FR.UTF-8`/`fr_FR.utf8` 三个 OS 名（有则沿用上游路径），全缺时装入合成法语 facet（`numpunct<char/wchar_t>::do_decimal_point` 返回 `,`），再跑同一 `ASSERT_EQ(converted,"1.23456e+05")` 并恢复 `classic`。`GTEST_SKIP` 整段删除，预期 `43/43/43/0/0` |

## 源码修改

`patches/0001-test-StringFunctions-locale-fallback.patch`（唯一补丁，`portability`）：仅改
`test/src/test_StringFunctions.cpp` 的 `FloatToStrLocale` 用例的 locale 获取逻辑——先试 OS
`fr_FR` 系列名，全缺时装入合成逗号小数点 facet，再跑同一断言；库源码零修改。第 11 轮起不再执行 CMake，
全部 OHOS 适配收敛为 `conanfile.py` 内的直编接线（上游
src/CMakeLists.txt 的精确 42 个 .cpp + 等价 defines/-I，C++14；
E57Export.h 按 GenerateExportHeader 语义现场生成；测试走
test/src 精确源集 + TEST_DATA_PATH 等价值）。此前各轮经
`_patch_sources` 的 CMakeLists 改写已随 CMake 流程一并移除。
RREV pin（requirements/test_requires，见上表 9）保留。

## 依赖版本

- xerces-c/3.2.5 (本仓已归档, 编译依赖)
- gtest/1.17.0.1 (本仓已归档, 仅上游测试编译用 `test_requires`, 不传播)

## 验证结果

待真机预检 (conan create: 编译 + 上游 `ctest --output-on-failure
--verbose` + test_package 两个消费者用例)。预检日志中的实测数字将
回填 PR 正文的通过率, 本轮不预填结果。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 主配方 (CMake, 静态库, 上游测试开关常开) |
| conandata.yml | 官方源码 URL + sha256, 测试数据 URL + sha256 |
| manifest.yaml | 版本交叉校验元数据 |
| test_package/ | 消费者测试: 版本契约 (7 检查) + 写读回环 (13 检查) |

## 注意事项

- `E57_VALIDATION_LEVEL` 保持上游默认 `1` (basic), 与上游 CI 一致。
- `test_StringFunctions.cpp` 仅静态构建时编译, 默认 `shared=False`
  下 6 个用例全部参与, 共享库模式下上游自动排除。
- `notes.md` 中文由 UTF-8 直接书写, 无 BOM。
