# libsolace 0.4.1 适配笔记

## 编译环境

- 构建系统: **cmake**（上游根 `CMakeLists.txt`，`project(solace)`；`./configure` + `Makefile.in`
  是上游开发期包装，本配方不走它）
- 编译日期: 2026-09-29
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，libc++ 15004）
- Conan profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS / os.version=6.0 / arch=armv8 /
  compiler=clang 15 / libc++ / **cppstd=17** / build_type=Release）
- 状态: built

## 编译步骤

1. `export_sources()`：`export_conandata_patches()` 把 `patches/0001-drop-conan1-bootstrap.patch`
   导出到配方目录。
2. `source()`：`get()` 下载 GitHub tag 归档 **zip**（URL 形态逐字取自 conan-center-index 的
   libsolace conandata；sha256 三路取证见 conandata.yml 注释），`strip_root=True`；
   随后 `apply_conandata_patches()` 应用该补丁（conandata `strip: 1`，经 patch_ng 试贴通过）。
3. `generate()`：
   - 写 `CMAKE_PROJECT_INCLUDE` 注入文件到 conan 的 generators 目录（见问题 1）；
   - `CMakeToolchain` 钉 `PKG_CONFIG=False`（上游 `option(PKG_CONFIG …)` 默认 OFF，且上游
     `project(solace)` 未声明 VERSION，装出来的 `.pc` 会带**空 Version**，故不安装）。
4. `build()`：
   - `cmake.configure()` → `cmake.build()`（默认 `all`：`libsolace`）；
   - `cmake.build(target="test_solace")` —— 上游 `add_subdirectory(test EXCLUDE_FROM_ALL)`
     使测试目标**不在** `all` 里，必须显式构建；
   - 沙箱 HOME 下真跑 `test_solace`，解析 gtest 汇总行 + 三道反假绿硬断言（见问题 3）。
5. `package()`：`cmake.install()`（→ `include/solace/*.hpp` 49 个 + `lib/libsolace.a`）
   + `LICENSE` → `licenses/`。上游**无 `install(EXPORT)`**，包内不含 CMake config，
   消费者由 conan CMakeDeps 生成 `libsolace-config.cmake`（目标 `libsolace::libsolace`）。
6. `test_package/`：消费者从**已安装包** include + 导入目标 `libsolace::libsolace` 实调
   13 组共 **40 项**显式检查，`test()` 用 `self.run(…, env="conanrun")` 直跑（R34 反空壳）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游根 `CMakeLists.txt` 的 `include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)` + `conan_basic_setup()` 在 Conan 2 下必失败（该文件不再生成） | 上游配方面向 Conan 1.x；这两行同时承担「全局 include 路径」与「`CONAN_LIBS` 变量」两件事——上游 `src/CMakeLists.txt` 的 `target_link_libraries(${PROJECT_NAME} PUBLIC ${CONAN_LIBS})`、`examples/`、以及 `test/CMakeLists.txt`（只链 solace 与 rt）都靠它拿到 gtest 的头与库 | ① 用补丁 `patches/0001-drop-conan1-bootstrap.patch` 删除这两行（**与 conan-center-index 同包配方 `_patch_sources()` 的 replace_in_file 逐字等价**，经 `export_sources`/`apply_conandata_patches` 导出并应用）；② `generate()` 写 `CMAKE_PROJECT_INCLUDE` 注入文件，在 `project()` 之后、`add_subdirectory` 之前补回**同样的两条全局语义**：`include_directories(<gtest>/include)` 与 `set(CONAN_LIBS <gtest>/lib/libgtest.a)` ⇒ 上游其余 CMakeLists **零改动**，gtest 头/库接线位置与 conan 1 时完全一致 |
| 2 | 上游测试目标 `test_solace` 不会被默认构建 | `add_subdirectory(test EXCLUDE_FROM_ALL)` 把它排除在 `all` 之外 | `build()` 内显式 `cmake.build(target="test_solace")`；随后直接跑二进制（**不用** `cmake.test()`——`enable_testing()` 在 `test/` 子目录而非根，根目录 ctest 会 `Total Tests: 0` 假绿，device-facts §二.22） |
| 3 | 「能编译 ≠ 测了」：gtest 全绿也可能只是注册 0 用例 | gtest 空跑同样打 `All 0 tests passed` + rc=0 | 三道硬断言：`registered > 0`、`passed == registered`、`registered <= 源码宏 raw`，任一不符即 `ConanException` 使 `conan create` 失败；另加**覆盖自检**：凡 `test/**/*.cpp` 含 `TEST*` 声明却未出现在 `test/CMakeLists.txt` 源清单里即报错（防「新增测试文件忘挂」静默漏跑） |
| 4 | 源码宏 345 vs 实跑 333 对不上 | 12 处 `TEST/TEST_F` 声明整体在上游 `/* */` **块注释**内，任何构建（含上游 `make test`）都不编译 | 候选数法取 **N = max(345, 333) = 345**（审方克隆后 grep 得 345），申报 `NOT_RUN = 12` 并逐文件逐行号归因（`reports/test-report.md` §一）；断言口径 2093/1953 单列不参与 N |
| 5 | `src/version.cpp` 硬编码 `SOLACE_VERSION_MAJOR/MINOR/BUILD = 0/3/1` | **上游自身缺陷**：tag v0.4.1 未同步该常量，`getBuildVersion()` 返回 0.3.1 | **不改上游内容**（属上游语义、非平台可移植问题）；消费者测试只断言 `majorNumber == 0` 与 `build.empty()`（上游 `test_package/example.cpp` 的原始契约），并在 PR 正文「补充说明」披露 |
| 6 | `curl` 拉 codeload 归档超时（`Failed to connect to codeload.github.com:443`） | 设备出网差异（curl 与 urllib 走不同路径） | 改用 python `urllib`：**三路独立下载 sha256 逐字节同值**且与 conan-center-index 记录值一致；`conan create` 自身下载亦成功（日志 `Sources correctly downloaded …`），属下载工具差异、非版本不可得 |

## 源码修改

**1 个补丁** `patches/0001-drop-conan1-bootstrap.patch`（conandata `strip: 1`），
只改根 `CMakeLists.txt` 的两行：

```diff
 # Include common compile flag
 include(cmake/compile_flags.cmake)
 include(GNUInstallDirs)
-include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
-conan_basic_setup()
 
 # Configure the project:
```

- **修改原因**：Conan 2 不再生成 `conanbuildinfo.cmake`，`include()` 直接 FATAL。
- **等价补回**：这两行提供的两条全局语义由 `generate()` 写的 `CMAKE_PROJECT_INCLUDE`
  注入文件补回（`include_directories(<gtest>/include)` + `set(CONAN_LIBS <gtest>/lib/libgtest.a)`），
  见问题 1；上游各级 CMakeLists 其余部分零改动。
- **与权威配方一致**：conan-center-index `recipes/libsolace/all/conanfile.py`
  对同一文件用同一条 `replace_in_file` 删除同样的两行（补丁正文与之逐字等价）。
- **不涉及**：任何测试用例、任何断言、任何 `__OHOS__` 平台宏、任何镜像/`file://` URL
 （PF5/PF7/H4/L4 面全净）；补丁经 conan 内置 `patch_ng` `strip=1` 试贴通过。

## 依赖版本

- 交付依赖：**0**（上游 `conanfile.txt` `[requires]` 段为空 + conan-center-index 配方无
  `requirements()`；`ci/scripts/preflight_check.sh libsolace/0.4.1` → `[OK] 预检通过（无依赖需要检查）`；
  无 SSL/压缩/数据库等可选开关需要禁用）
- 构建期测试依赖（`test_requires`，不随包交付）：**gtest/1.17.0**
 （`conan download gtest/1.17.0 -r=ohpcd` 全量成功；包 ID `21b17f8b…` 的 info 与本机 profile
  精确一致 os=OHOS/os.version=6.0/arch=armv8/compiler=clang 15/libc++/cppstd=17/Release；
  上游钉 1.10.0，制品仓最高 1.17.0.2，取 1.17.0 实测 333/333 全过）
- 系统库：**无**（`nm -u libsolace.a` 无任何 libm 符号，源码与头亦无 `#include <cmath>`，
  故不声明 `system_libs`；上游 CCI 对 Linux 追加的 `m` 在本包无实证支撑）

## 验证结果（R51 三步法）

清点（N 候选数法、四口径不混用；完整表与差额归因见 `reports/test-report.md`）：

| 口径 | 数值 |
|---|---|
| ① 源码宏 raw（不解析注释 = 审方 grep 同形） | 345 |
| ①′ 源码宏（块注释剔除 = 实际编译面） | 333 |
| ② 框架注册数（gtest 运行期 `[ RUN ]`） | 333 |
| ③ 断言位点 raw / 去注释（不同单位，不参与 N） | 2093 / 1953 |
| ④ 消费者断言（鸿蒙特有，不进上游分母） | 40 |

**N = max(345, 333) = 345；N′ = 333。**

```bash
# 实跑证据（采信轮 reports/conan-create.log）
grep -n 'tests from .* test suites ran' reports/conan-create.log   # 333 tests from 29 test suites ran.
grep -n '\[  PASSED  \]'                    reports/conan-create.log   # [  PASSED  ] 333 tests.
grep -c '^\[       OK \]'                   reports/conan-create.log   # 333
grep -n 'HMBS_UPSTREAM_TEST_RESULT'         reports/conan-create.log   # 机器可读结果行
grep -n 'libsolace consumer checks'         reports/conan-create.log   # 40 run, 0 failed
```

- 上游：**333/333 PASS**，FAIL 0、SKIP 0、NOT_RUN 12（块注释内，归因见 test-report §一）
- 消费者：**40/40 PASS**
- 合计：**373/385 PASS，FAIL 0、SKIP 0、NOT_RUN 12**

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `include/solace/*.hpp` | 49 个头文件 | 上游 `install(DIRECTORY include/ …)` 原样安装 |
| `lib/libsolace.a` | 静态库 | `add_library(solace …)` 默认静态（`BUILD_SHARED_LIBS=OFF`） |
| `licenses/LICENSE` | Apache-2.0 | 上游根 LICENSE |

## 注意事项

- **不提供 `commands.json`**：纯库包（无 `bindirs`、无 `RUNTIME DESTINATION bin`），
  PF8 要求纯库包**必须没有** commands.json；CI L0k 判为 "library package, not required"。
- **不安装 `.pc`**：`PKG_CONFIG=False`（上游 `project(solace)` 无 `VERSION`，装出来的 `.pc`
  的 `Version:` 会是空串）；消费者用 conan `PkgConfigDeps` 时由 `package_info` 的
  `pkg_config_name=libsolace` 生成正确文件。
- **`shared` 选项**：声明但本任务只验证默认（静态）变体；`fPIC` 由 conan toolchain 的
  FPicBlock 自动落到 `CMAKE_POSITION_INDEPENDENT_CODE`。
- **架构面**：`murmur3.cpp` 的分支走 `__aarch64__` → `MurmurHash3_x64_128`，
  `#error "Unsupported CPU architecture"` 不可达（W0 三步裁量见 `$TASK_DIR/w0-evidence.md`）。
- **上游已知内容缺陷（不改）**：`src/version.cpp` 硬编码 0.3.1，`getBuildVersion()` 对
  v0.4.1 返回 0.3.1；已在 PR 正文披露。
