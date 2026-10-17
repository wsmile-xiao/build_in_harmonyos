# zug 0.1.2 适配笔记

## 编译环境
- 构建系统: cmake（上游 `add_library(zug INTERFACE)`，纯头文件库）
- 编译日期: 2026-09-19
- 编译器: clang/clang++（Harmonybrew OHOS SDK clang 15.0.4，profile `ohos-aarch64`）
- 状态: built（真机 conan-verify + 本地 CI 通过，制品由 CI 上传）
- 特殊说明: header-only 库，安装包内只有头文件与许可证，无 .so/.a/可执行文件

## 库简介

zug 是 Juan Pedro Bolívar Puente 实现的 C++ transducers 库：可组合、增量式、
流式的归约（reduction）工具集，风格类似 Clojure/ClojureScript 的 transducer。

- 上游仓库: https://github.com/arximboldi/zug
- 固定来源: tag `v0.1.2` 归档，SHA256 `75ff666a4ce1615b3ca26abbb17b10f5cb5cf5f86c9c293ec430c34750d3ea27`
- 许可证: BSL-1.0（Boost Software License 1.0，随包 `LICENSE`）
- 类型: header-only（INTERFACE library），要求 C++14/17
- 上游 `project(zug VERSION 0.1.0)` 与 tag `v0.1.2` 不一致（上游未同步
  CMake 工程版本号）；本包版本以固定 tag 为准，不改动上游版本号。

## Conan 配方说明

### 配方结构
- `conanfile.py`: header-library 变体配方（`cmake_layout` + `CMakeToolchain`/`CMakeDeps`）
- `conandata.yml`: 官方源码 URL + sha256 + 补丁声明
- `patches/`: 1 个补丁（上游测试目标漏链 Catch2）
- `test_package/`: 消费者测试（通用 16 断言）+ 鸿蒙专项测试（跨 TU，6 断言）+ `MANIFEST.yml`

### 关键配置
- `package_type = "header-library"` + `package_id(): self.info.clear()`：
  所有 settings 组合产物一致（同 archives/t/tau/1.0.0 变体 A）。
- `requires("boost/1.84.0", transitive_headers=True)`：zug 的公开头文件裸用 boost ——
  `zug/meta/*.hpp` 无条件 `#include <boost/mpl/...>`（15 个 mpl 头文件），
  `zug/skip.hpp` 在没有 `std::variant` 时还会回退到 `boost::variant.hpp`，
  消费者必须继承该依赖。
- `test_requires("catch2/2.13.10-r0")`：只服务上游测试构建，不进消费者依赖链。
- `zug_BUILD_TESTS=ON` / `zug_BUILD_EXAMPLES=OFF` / `zug_BUILD_DOCS=OFF` /
  `DISABLE_WERROR=ON`：只构建上游测试；上游 `example/CMakeLists.txt` 实际只有一个
  空的 `examples` 自定义目标，`doc/` 需要 doxygen/sphinx，均与测试无关。
- `cmake.build(target="tests")`：上游 50 个测试程序都被声明为
  `add_executable(... EXCLUDE_FROM_ALL)`，只由自定义目标 `tests` 聚合；而 zug 本身
  无编译产物，因此不显式指定 `tests` 目标时 `cmake.build()` 什么都不会编出来。
- `cmake.test()`：在构建目录内执行 CTest，50 个用例全跑（层 1 上游官方测试）。
- `CMakeToolchain.extra_cxxflags` 追加 `-isystem <boost>/include`：见下「平台适配」第 2 条。
- `package()` 手工拷贝 `zug/**/*.hpp` 到 `include/zug`，不跑 `cmake.install()`：
  上游会 `install(EXPORT ZugConfig DESTINATION lib/cmake/Zug)`，装进包里会与
  Conan 生成的 `zug-config.cmake` 形成两套 CMake 包文件，`find_package` 语义
  变得不确定；只保留 Conan 一份（`cmake_file_name=zug`、`zug::zug`）。

### 平台适配
1. **R32 平台判断**：`self.settings.os in ("Linux", "OHOS")`，不用 `== "Linux"`。
2. **boost 头文件缺口（本包唯一实质平台问题）**：上游 CMakeLists 从不
   `find_package(Boost)`，但 `zug/meta/*.hpp` 等公开头文件里是裸的
   `#include <boost/mpl/...>`，因此以 Conan 依赖为准，在 `generate()` 里把
   `boost` 包目录的 include 路径通过 `CMakeToolchain.extra_cxxflags` 追加
   `-isystem`（不用 `CMAKE_CXX_FLAGS` 缓存项，避免顶掉 profile/conf 已有 flag）。
   这与 E480（`skip_binaries` → `transitive_headers/transitive_libs`）同源：
   依赖关系在配方层表达，不改上游源码。
3. **未使用平台宏**：补丁与配方均无 `__OHOS__`（PF5/R8）；无共享前缀注入
   （PF6/R49）；源码 URL 只有官方 https 地址（PF7/R39）。
4. **E092（CMake 不认识 OHOS）未触发**：设备 profile 的 build/host 同构，
   Conan `CMakeToolchain` 不写出 `CMAKE_SYSTEM_NAME`，CMake 用本机探测结果，
   真机 50 个测试程序编译链接全通过，因此本包不需要 CLI11 那套
   `CMAKE_SYSTEM_NAME=Linux` 规避。若 CI worker 上出现 E092，按该先例补即可。
5. `-Werror`：上游在非 MSVC 且未设 `DISABLE_WERROR` 时强制 `-Werror`；
   本包设 `DISABLE_WERROR=ON`，避免 OHOS clang15 的额外告警把纯告警变成失败。

## 依赖

- `boost/1.84.0`（制品仓已发布，`conan download` 取 aarch64/OHOS 制品通过）
- `catch2/2.13.10-r0`（同上，仅 test_requires）
- 未新增/修改任何共享工具链、未捎带适配新依赖（W0 只读校验）。

## 测试说明

### 上游测试（层 1）
- 位置 `test/`：49 个 `test/**/*.cpp` 各自编成一个 Catch2 可执行文件，
  外加 `test/__inline_var_tests/`（4 个 .cpp 编成 1 个程序），共 **50 个**
  CTest 用例（`add_test("test/<output>" <output>)`）。
- 执行方式：`cmake.build(target="tests")` + `cmake.test()`，即 `ctest`。
- 真机结果：**100% tests passed out of 50**（首过，无跳过、无豁免），
  逐程序 Catch2 汇总 **253 断言 / 194 用例**，见 `reports/`。
- 上游测试用例本身未修改（唯一改动是补丁给一个测试目标补链接依赖，见下）。

### test_package（层 2）
- `test_zug.cpp`：只用已安装的 `<zug/...>` 头文件，验证 `comp`/`operator|`、
  `into`/`into_vector`、`transduce`（含变长 zip 与提前终止）、`reduce` +
  `last` reductor、`range`/`count`/`cycle` 生成器、`transducer<In,Out>` 类型擦除，
  共 16 条断言；断言失败返回非 0，`test()` 用 `self.run` 真实执行。
- `test_zug_ohos.cpp` + `test_zug_ohos_tu2.cpp`：鸿蒙专项，跨翻译单元传递
  `zug::transducer<int, std::string>` 并完成转导（验证 OHOS clang15/libc++ 下
  擦除类型的实例化、typeinfo/vtable 一致性）、无状态管道连续复用结果一致、
  101 元素深实例化折叠，共 6 条断言。
- 依赖可见性即测试点之一：test_package 只 require 被测包，不显式声明 boost，
  能编译过即说明 `transitive_headers` 生效。

## 验证结果

```bash
# 1) 干净构建 + 上游官方测试（conan-verify G2，与平台 CI 同源）
python3 scripts/ohc-run.py conan-verify zug 0.1.2 --profile ohos-aarch64-device
#   → G1/G0/G2/G3/G4 全 PASS，"✅ 配方验证通过: zug 0.1.2"，rc=0
#   → reports/conan-create.log: "100% tests passed out of 50"

# 2) 本地 CI 门禁（L0/L1/L2/L4/L5 + KC/JC）
CONAN_PROFILE=ohos-aarch64-device CI_PACKAGES=archives/z/zug/0.1.2 \
  zsh ci/conan/build_and_test.sh archives/z/zug/0.1.2
#   → L0_RESULT=pass: all checks passed；JC_RESULT=pass（incremental，13 文件）；KC_RESULT=pass
#   → L1_RESULT=pass: test_package executed；L1e 破坏性反向验证 pass（移走 include/ 后 conan test 失败）
#   → "100% tests passed out of 50"、test_zug: 16/16、test_zug_ohos: 6/6
#   → Pass rate: 100.0% (1/1)，退出码 0
#   （L2 skip / L4 warn / L5 warn 均为 header-only 预期，见 reports/test-report.md 门禁表）

# 3) 消费者视角单测（对已创建包复跑 test_package）
conan test archives/z/zug/0.1.2/test_package zug/0.1.2@ohpcd/stable \
  -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device
#   → test_zug: 16/16 assertions passed
#   → test_zug_ohos: 6/6 assertions passed (cxx=201703, sizeof(void*)=8)

# 4) 提交前硬闸自查（只剩 PF9 对软件级 README/manifest 的已知假阳性）
python3 scripts/ohc/preflight.py . origin/main HEAD

# 5) 依赖发布与产物形态
conan download boost/1.84.0@ohpcd/stable -r ohpcd      # W0：依赖已在制品仓
#   包内容 = include/zug/**.hpp 共 83 个 + licenses/LICENSE；无 bin/、无 lib/（header-only）
#   逐程序 Catch2 汇总：50 程序 / 253 断言 / 194 用例（reports/upstream-catch2-per-program.log）
```

## 源码修改

只有一个补丁，且是上游自身缺陷，不是平台差异：

1. `patches/0001-test-__inline_var_tests-CMakeLists.txt.patch`
   - 现象：`test/__inline_var_tests/CMakeLists.txt` 里
     `target_link_libraries(inline_var_tests PUBLIC zug-dev)`，而 `test/CMakeLists.txt`
     为其余 49 个目标写的是 `... zug-dev Catch2::Catch2)`。该目录源码
     `#include <catch2/catch.hpp>`，于是开启 `zug_BUILD_TESTS` 后这个目标
     在本机也编不过（`'catch2/catch.hpp' file not found`）。
   - 修改：与父目录其它测试目标保持一致，补上 `Catch2::Catch2`。
   - 性质：跨构建系统可移植的上游构建缺陷修复（`patch_type: portability`，
     code-style §12 固定取值），不含任何平台宏、不改任何测试断言逻辑。

## 已知限制 / 后续

- boost 不可降为可选：`zug/meta/*.hpp` 无条件依赖 `boost/mpl`（C++17 下 `zug/skip.hpp`
  走 `std::variant`，但 mpl 那部分始终需要 boost 头文件）。
- 上游 `test/CMakeLists.txt` 用 `list(FILTER ... EXCLUDE REGEX
  "${CURRENT_CMAKE_DIRECTORY}/__*")`，其中 `CURRENT_CMAKE_DIRECTORY` 并非
  CMake 变量（展开为空），实际生效的正则是 `/__*`。当前恰好正确排除了
  `test/__inline_var_tests/`，故未修改；若上游改名目录结构，此处的用例会漂移。
- 未生成 `commands.json`：纯库包（R38 口径，库类型不应有）。

## 问题与解决方案

> 表头不带序号列：`submit` 的 notes 抽取器按 `| 问题 | 根因 | 解决方案 |` 三列取
> `cols[1..3]`，多一列序号会让字段整体错位。

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| 开启 `zug_BUILD_TESTS` 后 `inline_var_tests` 报 `'catch2/catch.hpp' file not found` | 上游 `test/__inline_var_tests/CMakeLists.txt` 只链 `zug-dev`，漏了 `Catch2::Catch2`（其余 49 个测试目标都有） | 补丁 0001 补上 `Catch2::Catch2`，与父目录其它目标一致；未改任何测试用例 |
| 编译期找不到 `<boost/mpl/...>`（以及 C++14 回退路径的 `<boost/variant.hpp>`） | 上游 CMakeLists 不 `find_package(Boost)`，Conan 依赖不会自动出现在编译行的 include 路径里 | `requires("boost/1.84.0", transitive_headers=True)`，并在 `generate()` 里用 `CMakeToolchain.extra_cxxflags` 追加 `-isystem`（值取自依赖对象，不读 shell 环境变量，R33） |
| `cmake.build()` + `cmake.test()` 报告通过，但一个测试都没编出来 | 50 个测试程序全是 `EXCLUDE_FROM_ALL`，而 header-only 包的默认构建目标是空的 | 显式 `cmake.build(target="tests")` 再 `cmake.test()` |
| OHOS clang15 下构建被告警中断 | 上游在非 MSVC 且未设 `DISABLE_WERROR` 时强制追加 `-Werror` | 设 `DISABLE_WERROR=ON` |
| test_package 里以 `const&` 跨翻译单元传 `zug::transducer` 编不过 | `zug/meta.hpp` 用 `XformT()()` 求返回值类型，而 `transducer::operator()` 未标 `const` | 改用非常量引用传递；作为上游 API 约束记入已知限制 |
| 本地 `finish`/`conan-verify` 的 G2 报缺 `/data/service/hnp/bin/clang` | 仓库内 `ci/conan/profiles/ohos-aarch64` 写的是 CI worker 路径，本机 SDK 在 `.harmonybrew` 下 | 临时把该 profile 文件移开，使工具按 profile 名回退到设备侧同名 profile（settings 完全一致），跑完后按 sha256 校验还原；未改动任何仓库文件 |

## 对话记录

- 问：zug 需要打几个补丁？ 答：1 个。全部平台差异都在配方层（依赖声明 + include 注入 + 构建目标选择），上游源码零逻辑介入。
- 问：为什么不调用 `cmake.install()` 装上游的 CMake 包文件？ 答：上游会 `install(EXPORT ZugConfig DESTINATION lib/cmake/Zug)`，与 CMakeDeps 生成的 `zug-config.cmake` 并存两套包文件，`find_package` 语义不确定；改由 `cpp_info` 提供 `cmake_file_name=zug` 与 `zug::zug`。
- 问：E092（CMake 不识别 OHOS）为何没做规避？ 答：设备侧 build==host 时 Conan 的 CMakeToolchain 根本不写 `CMAKE_SYSTEM_NAME`，实测 50 个测试程序编译、链接、运行全通过；若平台 CI 命中，按 `archives/c/CLI11/2.6.2` 先例补 `CMAKE_SYSTEM_NAME=Linux`。
- 问：测试有没有被削弱或走白名单？ 答：没有。50/50 CTest 全量执行，无豁免，`zug` 不在 `ci/config/no_official_test.txt` 中。

## W4 独立审计处置

审计报告：`reports/audit-result.json`（`scripts/pre_pr_audit.py generate` 出输入，独立子任务出结论）。
结论 **pass**，P0=0 / P1=0 / P2=2 / P3=5，逐条处置：

| # | 级别 | 发现 | 处置 |
|---|------|------|------|
| 1 | P2 | `conanfile.py` 残留 `url = ""  # CI fills this`（code-style §5 明确列为未完成项） | 已填官方仓库地址 |
| 2 | P2 | `patch_type: "bugfix"` 与 §12 固定值不符 | 已改 `"portability"`，`manifest.yaml` 的 patch_classification 同步 |
| 3 | P3 | `conandata.yml` 的 `patches:` 用版本键分层，与 §13 示例及仓内多数写法不一致，按 list 读 `data["patches"]` 的脚本会拿到 dict | 已改扁平列表（两种形态 Conan 都支持，改后与仓内一致） |
| 4 | P3 | `package_info()` 未显式设 `cpp_info.libs`（§4） | 已补 `self.cpp_info.libs = []` |
| 5 | P3 | 用 `CMAKE_CXX_FLAGS` 缓存项注入 include，可能顶掉 profile/conf 已有 flag | 已改用 `CMakeToolchain.extra_cxxflags` 追加（`tc.extra_cxxflags` 在 conan 2.29.1 存在，aiksaurus/aldo 有先例） |
| 6 | P3 | 交叉构建跳过 50 个用例时只 `output.info`，且文档表述无条件 | 两处提升为 `output.warning`；docstring 与软件级 README 补「真机 build==host 实测」限定 |
| 7 | P3 | `notes.md` / `test_zug.cpp` 把 boost 必需性归因于 `zug::transducer` 的 `boost::variant` | 已更正：`transducer` 用 `std::function` + `any_state` 擦除，`zug/skip.hpp` 的 variant 只在 C++14 分支生效；boost 的真实必需项是 `zug/meta/pack.hpp` 裸用的 `boost/mpl` |

审计方另外做了脱离作者叙事的独立复核：重抓官方 `v0.1.2` tag 比对 sha256、清点 53 个 `.cpp` → 50 个
CTest 用例、逐条核对 `MANIFEST.yml` 的用例数与上游 `TEST_CASE` 静态计数、把补丁上下文与上游文件
逐字节比对，均未发现不符。

---

**编译结束**: 2026-09-19 21:46
**最终状态**: built
