# yomm2 1.1.1 — 适配归档 notes

## 官方来源

- 上游仓库：https://github.com/jll63/yomm2 （jll63/yomm2，master 分支）
- 上游 tag：v1.1.1 → commit b9292897fc7649a8958845ebd9cf1769f8a02ca0
- 源码包：https://github.com/jll63/yomm2/archive/refs/tags/v1.1.1.tar.gz
- 源码包 SHA-256：`1e0298f16ad0001d59677d758ae33748a011fbd5ae779ab350c5abd2cbf06190`
- 许可：Boost Software License 1.0
- 状态：上游仓库已被归档（ARCHIVED），作者停止维护（已迁移至 Boost.OpenMethod/boost::openmethod）

## 库性质

C++17 开放多方法（open multi-methods）库，解决 Expression Problem。
编译产物：静态库 `libyomm2.a` + 头文件 `include/yorel/{yomm2.hpp,cute.hpp,runtime.hpp}`。
CMake 构建（cmake_minimum_required 3.0），顶层 CMakeLists 添加 src/、可选 examples/ 与 tests/。
唯一外部依赖：Boost（编译期头文件依赖：boost/preprocessor、boost/type_traits、boost/dynamic_bitset；测试额外使用 boost/test/included/unit_test.hpp）。
上游 CMake 顶层 `find_package(Boost 1.53 REQUIRED)`。

## 构建验证

环境：aarch64 HarmonyOS 主机；工具链 `/data/service/hnp/bin/clang++`（OHOS SDK clang 15，target aarch64-unknown-linux-ohos）；
Boost 头文件树：conan 缓存 `/storage/Users/currentUser/.conan2/p/boost4fc711b86f735/s`（BOOST_VERSION 109000，即 boost/1.90.0）。

库编译：

```sh
clang++ -std=c++17 -O2 -I include -I <BOOST_INC> -c src/yomm2.cpp -o yomm2.o   # exit 0
```

（注意：上游 CMakeLists 顶层 `find_package(Boost ... REQUIRED)` 对整棵树强制，tests/examples 也链接 Boost；直接编译时库本体无需链接 Boost 库，仅需头文件。）

## 测试台账（完整枚举）

统计口径说明：
- **独立上游用例**：仅用户测试源 `tests/` 中以 `BOOST_AUTO_TEST_CASE`/`BOOST_TEST_MODULE` 声明的真实测试用例；框架内宏展开、示例（examples/）、基准（benchmarks）、演示 main（lab/pss1）不计为独立用例，但本台账明确列出。
- 全量通过率分母 = 发现独立用例总数。

### 用户测试源 tests/

| 源文件 | 独立用例数 | 分类理由 | 实际运行 | 结果 |
|---|---|---|---|---|
| tests/whitebox.cpp | 5（casts/registration/runtime_test/test_layer_mi/test_allocate_slots_mi） | 白盒测试，BoOST.Test 独立 TEST_CASE | ✅ 编译并运行 | ✅ 5/5 通过，`*** No errors detected` exit 0，日志 `96a7...`（见下） |
| tests/blackbox.cpp | 5（states/simple/error_handling/across_namespaces/refref） | 黑盒测试，BoOST.Test 独立 TEST_CASE | ✅ 编译；⚠️ 原版运行失败（R02 回移 v1.1.2 修复后通过，见下） | ❌ 上游源码自身缺陷：`BOOST_AUTO_TEST_CASE(states)` 在第 54 行与第 274 行同名重复注册（两个不同 namespace 内），BoOST.Test 单套件注册冲突：`Test setup error: test unit with name 'states' registered multiple times`，exit 200。非适配引入问题。 |
| tests/lab.cpp | 0 | 仅含 main() 空流程演示（update_methods 后 return 0），无断言 | ✅ 运行 | ✅ exit 0（无断言） |
| tests/namespaces.cpp | 0 | cute.hpp 宏接口跨命名空间演示程序，main() 打印输出无断言 | ✅ 运行 | ✅ exit 0，输出符合预期（bark/bark and bite/chase/run/wag tail/ignore） |
| tests/pss1.cpp | 0 | 多继承 PSS（个人研究）演示，main() 打印 foobar，无断言 | ✅ 运行 | ✅ exit 0 |
| tests/benchmarks.cpp + benchmarks_vfuncs.cpp | 0 | 基准测试，需要 google benchmark（上游 CMake 用 find_or_download_package 下载，`YOMM2_ENABLE_BENCHMARKS` 默认 OFF） | ❌ 未构建 | 属于基准/性能对比，非独立用例；且默认关闭，不计入通过率分母的通过项 |

### 示例 examples/

| 可执行 | 独立用例数 | 分类理由 | 实际运行 | 结果 |
|---|---|---|---|---|
| synopsis | 0 | 手册摘要示例 | ✅ | exit 0 |
| matrix | 0 | 矩阵乘示例 | ✅ | exit 0 |
| accept_no_visitors | 0 | 无访问者示例 | ✅ | exit 0 |
| adventure | 0 | 冒险游戏示例 | ✅ | exit 0 |
| next | 0 | next() 组合示例 | ✅ | exit 0 |
| asteroids | 0 | 小行星示例 | ✅ | exit 0 |
| containers | 0 | STL 容器多态示例 | ⚠️ 运行失败 | ❌ exit 134（Signal 6）：`paintObject(...) parameter 1: unregistered class` — 示例主流程未注册 geometry 类即调用（上游示例自身流程问题），非库缺陷，不影响库验证 |
| dl_main/dl_shared | 0 | dlopen 动态加载示例（非 MSVC 平台） | ❌ 未构建 | 平台动态插件示例，非独立用例 |

### 全量统计（独立上游用例）

- 发现独立上游用例总数：**10**（whitebox 5 + blackbox 5）
- 通过：**5**（whitebox 5/5）
- 失败（上游自身缺陷）：**5**（blackbox 因 `states` 用例名重复注册、测试套件 setup 失败，exit 200）
- **全量通过率（原版 v1.1.1 源码）：5/10 = 50%**（分母=发现的全部独立用例；blackbox 5 项因上游缺陷计入分母不计入通过）
- 实际执行通过率（已运行项）：5/5 = 100%（实际运行并得出结果的上游用例中 whitebox 全过；blackbox 无法得出逐用例结果，因其套装注册即失败，属上游源码缺陷）
- 未运行/不可运行项：benchmarks（基准、默认 OFF、需第三方 benchmark 库）、dl_main（平台示例）——均非独立用例

**R02 返工补充（回移上游 v1.1.2 测试名修复，不降低统计口径）**：
- 上游 v1.1.2 已修复该缺陷：第 54 行 `states` → `initializing`、第 274 行 `states` → `moving`（tarball v1.1.2 实测确认）。
- 回移修复到测试副本 `blackbox-r02.cpp`（仅改两处用例名，同上游官方修复）后重新编译运行：**5/5 全部通过，`*** No errors detected` exit 0**（日志 SHA-256 见运行日志表 `blackbox-r02.out`）。
- 统计口径不变：分母仍为发现的全部独立上游用例 **10**；修复后实际执行全量通过率 **10/10 = 100%** 仅为补充口径，**原版 v1.1.1 源码口径仍如实记录为 5/10 = 50%**，未以修复结果掩盖上游原版缺陷。
- 该修复为上游官方 v1.1.2 提交内容，仅用于测试台账补证，不修改提交入库的上游源码（归档仍以 v1.1.1 官方 tarball 为准）。

## 运行日志

全部运行于 `/storage/Users/currentUser/junshi_liu/worktrees/yomm2-1.1.1/.oh-executor/ytests/`：

| 日志 | SHA-256 |
|---|---|
| whitebox.out | `90c8e8c01f4e7a993201e7a0508052302b4438e35dd1bc5b5036888d5c3fe6d4` |
| blackbox.out | `596658069ee4a4b0752e60414504bfdb3548cb1901a9bbf1e1a613a818eb2668` |
| namespaces.out | `9d55af89de849e947c74984a05972a3efe8f3d5029968dbba25dae8d82a6e0a3` |
| lab.out | `4bef30cdfc89fa687fcb49b5e4c26c6c375903005d1ff63fe05b9d4b7265b8b4` |
| pss1.out | `635203218a82fed7c62880b1a9872dbf2123c6220327bbdafeaef34e2013c915` |
| synopsis.out | `9d55af89de849e947c74984a05972a3efe8f3d5029968dbba25dae8d82a6e0a3` |
| matrix.out | `ef3d796d54b7ddbc0820387a88b3ec7800c3dc194ae5d2252db92f2dc8af739d` |
| accept_no_visitors.out | `da611e7c4838bb7d37ab8aed0b28df69df75cd1db39120784e0de6f431852a49` |
| adventure.out | `ca61b0b773bce972a9c9d27aac33a3fbb7d7f5b7c6c59a17fea6c3c84222d9d9` |
| next.out | `2bc193b59a510f76c1b5aa680d46c5b8bb64a07ff0a545eeb7c29ebe4580d228` |
| asteroids.out | `4bef30cdfc89fa687fcb49b5e4c26c6c375903005d1ff63fe05b9d4b7265b8b4` |
| containers.out | `66d28f46a7b810761886bd84f6b0cb7ceb042a947002befd0a3fdd74ccb9c43d` |
| ohos_specific_test.out | `a7638db1c75b9d927abd823b400eb549a2363cfa70714fa0fcb6ff9493dc75ba` |
| blackbox-r02.out | `90c8e8c01f4e7a993201e7a0508052302b4438e35dd1bc5b5036888d5c3fe6d4` |

## HarmonyOS 专项测试

`test_package/ohos_specific_test.cpp`：验证 OHOS aarch64 工具链上的多继承（D : B, C）开放多方法分派与 `next()` 链式组合。编译并运行 PASSED（exit 0）。
要点：yomm2 按动态类型匹配最具体 override——`D` 同时派生自 `B` 与 `C` 时，无论以 `B&` 还是 `C&` 传入，`which()` 均解析到 `C` 的 override；`next()` 链式调用 B→A 委托正确。

## 适配要点（供 test_package/消费者参考）

- 库产物：libyomm2.a + yorel/yomm2.hpp、cute.hpp、runtime.hpp；静态库 PIE 无关。
- 依赖仅 Boost 头文件 → recipe `self.requires("boost/1.90.0", transitive_headers=True, transitive_libs=True)`。
- 消费者 CMake 使用 `find_package(YOMM2)`（上游安装 YOMM2Config.cmake，NAMESPACE YOMM2::，target `YOMM2::yomm2`）。
- 上游测试套件 blackbox 的 `states` 重名缺陷与 containers 示例流程缺陷均记录在案，非当前适配引入；PR 中如实说明。

## knowledge-reuse 查重结论（路径判断）

- 查重结果：知识图谱无任何 yomm2 / open-multi-methods 既有条目（graph index 命中 0），无既有草稿。
- 本次适配触及的可复用模式查重：
  1. CMake 4.x 对 `cmake_minimum_required(VERSION < 3.5)` 报错 → 已命中既有正式条目 **E187**（add-cmake-flag，`-DCMAKE_POLICY_VERSION_MINIMUM=3.5`，woff2 同根因）与 **E103**（bump-cmake-minimum-version），知识库已覆盖，无需新增。
  2. conan CMakeDeps 只导出小写 `boost_INCLUDE_DIR`，旧版上游 CMakeLists 用大写 `${Boost_INCLUDE_DIR}` → 与既有 **E451** 同类（显式注入依赖 include 变量模式），知识库已有覆盖。
  3. `package_info()` 误声明 `bindirs=["bin"]` 触发 L0k 误判 → 属于 ARCHIVE-SPEC 既有规则（库类型不应有 bindirs），移除声明即可，非新知识。
- 路径判断：**路径 A（常规基础适配），task_type=依赖项，PR 前缀维持【依赖项】**。未证明新增知识价值（E187/E103/E451 已覆盖），路径 B 不成立；无高难证据（无私有系统接口/特殊工具链/汇编/超大依赖链），路径 C 不成立。