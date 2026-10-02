# DRAFT-lldb001 — gtest 1.17 × LLVM/lldb 类型不兼容（Message 流式 + 容器匹配器）

**错误签名**（两条独立）：
1. `invalid operands to binary expression ('std::stringstream' and 'const llvm::StringRef')` — gtest 消息流式
2. `no type named 'value_type' in 'lldb_private::RangeVector<...>'` — gmock 容器匹配器

## 根因 ①：Message 流式（FormatEntityTest.cpp:177 类错误）
- gtest 1.17 `testing::Message::operator<<`（gtest-message.h:148）：`*ss_ << val;` 无 SFINAE 保护，靠 **ADL** 在调用点找 `operator<<(std::ostream&, T)`。
- LLVM 22.x 头只有 raw_ostream 重载（llvm/ADT/Twine.h:544），**没有** std::ostream<<StringRef/Twine/SmallString（两棵源树 Twine.h 完全一致，已排除版本差）。
- 任何把 .str() 族类型流进 gtest 消息的断言（`EXPECT_TRUE(x) << strref << ...`）硬错误。
- 排除项：LLVM 侧 SupportHelpers.h 无该 operator（仅局部 matcher/PrintTo）；wrapper gtest 树=纯上游 1.17（llvm/googletest 仓库 404，子模块实为 google/googletest）。

## 根因 ②：gmock 容器匹配器 value_type（RangeMapTest.cpp:24 类错误）
- gmock 1.17 ElementsAreMatcher：`typedef typename View::value_type Element`（gmock-matchers.h:3947）硬要求标准容器 typedef。
- lldb `RangeVector`（RangeMap.h:136）= 自定义容器（`Collection = llvm::SmallVector<Entry, N>`，非 vector 派生），无 value_type。
- **级联噪声**：value_type 硬错误后 clang 错误恢复产生假的 `std::equal_to<>()(Range, int)` 实例化错误（MatchAndExplain<int>）——补 value_type 后整条链消失，勿被带偏去改 operator==（Range::operator== 本就存在且可用）。

## 修复（最终方案：vendored 树，V9 全量实测验证）

**首选：消费归档内置 vendored 树（补丁 0004，lldb/cmake/modules/LLDBStandalone.cmake）**
- LLVM 22.1.0 官方 release tarball 顶层内置 `third-party/unittest`（LLVM-patched googletest，monorepo CI 同源）——wrapper 的 `LLVM_HAS_GTEST` 模式构建合并 `llvm_gtest`/`llvm_gtest_main` 目标（gtest-all.cc + gmock-all.cc），两条根因均不出现：
  - 根因①：vendored gtest 内置 `printable` raw_ostream 流式桥（.str() 族类型可流式）
  - 根因②：vendored gmock 容器匹配器可直接编译（单 TU 双实验实证，无需 value_type）
- 接线三要素：①`set(LLVM_HAS_GTEST ON)`；②`get_filename_component(_root "${LLVM_MAIN_SRC_DIR}" DIRECTORY)` 解析 monorepo 根 → `EXISTS ${_root}/third-party/unittest/CMakeLists.txt` 源树优先 `add_subdirectory`；③`LLVM_THIRD_PARTY_DIR` 包内回退（EXISTS 守卫，standalone 消费方静默 no-op）
- 实测：lldb/0.0.1 V9 全量 946/946 构建边 + gtest 31387 用例（31359 pass / 28 fail 全部设备沙箱归因）
- 优点：monorepo 同源（版本溯源零偏移）、无 conan googletest 依赖、CI `LLDB_INCLUDE_UNITTESTS=OFF` 时该接线不激活

**已弃用 fallback：shim + value_type（原补丁 0009/0010，仅存 git 历史，vendored 树不可用时才用）**
1. **shim（原 0009）**：`lldb/unittests/CMakeLists.txt` 目录级 `file(WRITE)` 生成 SFINAE shim 头至构建目录（`namespace llvm` 内模板，对 .str() 可转 std::string 的类型提供 `std::ostream<<`，ADL 命中）+ `-include` 强制包含（仅 unittest TU，liblldb 编译标志零污染；构建期生成 = 补丁零新增文件，规避 refresh-patch a/a/ 前缀加倍 bug）。
2. **value_type（原 0010）**：RangeVector 补 `typedef Entry value_type;`（1 行，无语义变化）。

## 环境注记
- LLVM 22.x monorepo 的 gtest 从 `llvm/third-party` 迁至顶层 `third-party/unittest`（GitHub API 实证 llvm/ 内已无 third-party；22.1.0 官方 release tarball 顶层实证含 third-party/unittest）——独立构建应优先消费 vendored 树；用标准 googletest 1.17（如 conan 包）必现本模式。
- 本地构建机 clang 15.0.4（hnp，aarch64-unknown-linux-ohos），monorepo CI 用新版 clang——本模式与编译器版本无关（纯头文件 SFINAE/typedef 要求），两代编译器同现。

## 验证
- 首选路线（vendored）：V9 全量 946/946 构建边 + gtest 31387 用例实测（见 lldb/0.0.1 notes.md + reports/test-report.md）。
- 已弃用路线（shim+value_type）历史验证：单 TU `ninja unittests/Utility/CMakeFiles/UtilityTests.dir/RangeMapTest.cpp.o` 0 错误；V5→V7 FormatEntityTest.cpp（根因①首例）编译通过。
