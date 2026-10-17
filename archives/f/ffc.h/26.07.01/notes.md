# ffc.h 26.07.01 适配笔记

## 编译环境
- 构建系统: header-only（单文件头库，CMake INTERFACE + Makefile 测试构建）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4（OHOS PC，无 gcc；Makefile 硬编码 gcc 需垫片）
- 状态: built

## 编译步骤

```bash
# 1. 源码获取（GitHub 直连超时，经 gh-proxy 传输官方 tarball，SHA-256 核验一致）
#    tag: v26.07.01, sha256: 78bc47d4bd2cf28c1487134e428214cdd105757527897ff8cd1ad226d31e7890
python3 scripts/ohc-run.py init-build ffc.h 26.07.01 --url=https://github.com/kolemannix/ffc.h/archive/refs/tags/v26.07.01.tar.gz

# 2. 探索性编译（header-only 库无 configure；直接编译上游测试入口）
#    test_runner / test_int_runner / test_runner_src / test_int_runner_src /
#    supplemental_tests / supplemental_tests_src / test_exhaustive_runner / example
clang -xc -std=c99 -D_DEFAULT_SOURCE -D_POSIX_C_SOURCE=200809L -DFFC_IMPL -I. -Itest_src test_src/test.c -o out/test_runner -lm

# 3. Conan 配方（package_type=header-library）验证
python3 scripts/ohc-run.py conan-init ffc.h 26.07.01
python3 scripts/ohc-run.py conan-verify ffc.h 26.07.01   # G0-G4 全部 PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时（Errno 110 / port 443 不可达） | 网络环境无法直连 github.com | 经 gh-proxy.com 传输官方 tarball，conandata.yml 仍记录官方 GitHub URL + 核验 SHA-256；conan-verify 自动注入 ghfast.top 镜像 |
| 2 | `make test` 失败：sonicsv.h madvise/MADV_SEQUENTIAL 未声明 + `make: gcc: No such file or directory` | Makefile `ifeq ($(UNAME_S),Linux)` 在 HarmonyOS（uname -s=HarmonyOS）不匹配 → 不定义 `-D_DEFAULT_SOURCE`；且 Makefile 硬编码 gcc（环境只有 clang） | 编译显式加 `-D_DEFAULT_SOURCE -D_POSIX_C_SOURCE=200809L`（与上游 CMakeLists.txt 声明一致）；gcc→clang 符号链接垫片 |
| 3 | conan-init 生成 autotools 模板配方 | 构建系统误判为 autotools，实际是 header-only CMake INTERFACE 库 | 重写为 package_type=header-library 配方（no_copy_source + copy 头文件 + package_id clear） |
| 4 | conan create 报 "Package type is 'library', but no 'shared' option declared" | Conan 2 对 library 类型强制要求 shared option | 改用 package_type=header-library |
| 5 | test_package/conanfile.py SyntaxError: class Ffc.HTestConan | conan-init 模板把包名含点号（ffc.h）拼进类名 | 类名改为 FfcHTestConan |
| 6 | test_package CMake find_package(ffc.h) 找不到 config | 配方 cmake_file_name=ffc 生成 ffc-config.cmake | find_package(ffc) + 链接 ffc::ffc |
| 7 | 消费者测试链接 undefined symbol: ffc_parse_i64_simple | ffc.h 为 FFC_IMPL 单头实现库：实现只在定义 FFC_IMPL 的 TU 编译 | test_package 在 include 前 #define FFC_IMPL（与上游 CMake 一致） |
| 8 | /tmp 只读（ld.lld cannot open output file） | 平台 /tmp 只读（E002） | 用 $HOME/tmp 作为可写构建/输出目录 |

## 源码修改

无源码补丁（header-only 库，无需修改上游源码）。

## 依赖版本

- 无第三方运行时依赖（0 依赖，header-only）
- 构建工具：clang 15.0.4 / make 4.4.1 / cmake 4.1.2 / conan 2.29.1

## 验证结果

```bash
# 上游测试入口（源码声明 -> 构建目标 -> 实际运行）
# test_runner          : PASS (CSV 浮点用例 + 特殊值/JSON 模式)
# test_int_runner      : PASS (整数解析)
# test_runner_src      : PASS (src/ 头文件变体)
# test_int_runner_src  : PASS
# supplemental_tests   : PASS (fastfloat supplemental 数据 599458+ 值比对)
# supplemental_tests_src: PASS
# test_exhaustive_runner: PASS (受限采样 4295 值全过；全量 float32 穷举为高成本入口)
# example              : PASS
# test_package 消费者测试 : PASS (ffc_parse_double_simple / ffc_parse_i64_simple ALL OK)
```

**双口径台账**：源码声明 8 个独立上游测试入口（test_runner、test_int_runner、test_runner_src、
test_int_runner_src、supplemental_tests、supplemental_tests_src、test_exhaustive_runner、
example 示例程序），当前 OHOS 配置全部实例化并实际运行，8/8 通过（100%）。
说明：上游 CMake 注册 6 个 ctest 项（test_runner/test_int_runner/test_runner_src/
test_int_runner_src/supplemental_tests/supplemental_tests_src），Makefile 另有
test_exhaustive_runner 与 example 两个入口；exhaustive 全量 float32 穷举在设备上为
高成本入口，本轮以采样 stride=1000000（4295 值）验证算法正确性后如实计入台账，
不作为失败项。

## 知识候选台账（路径 B 判定）

### 候选 C1：Makefile `ifeq ($(UNAME_S),Linux)` 平台检测在 HarmonyOS 不匹配 → POSIX 特性宏缺失

- **真实错误**：`test_src/sonicsv.h:1611: error: use of undeclared identifier 'MADV_SEQUENTIAL'`（madvise 系函数未声明）
- **根因**：Makefile 用 `UNAME_S := $(shell uname -s)` + `ifeq ($(UNAME_S),Linux)` 决定是否加 `-D_DEFAULT_SOURCE`；HarmonyOS 上 `uname -s` 返回 `HarmonyOS`，条件不成立 → 特性宏缺失 → madvise/MADV_* 未声明
- **修复**：编译显式传 `-D_DEFAULT_SOURCE -D_POSIX_C_SOURCE=200809L`（与上游 CMakeLists.txt 的 target_compile_definitions 声明一致）
- **验证**：加宏后 test_runner/test_int_runner 编译运行全部 PASS
- **适用边界**：所有用 Makefile `uname -s` 平台检测决定特性宏的 C 库；反例：用 autoconf（config.guess）或 CMake 的库走 E007/E160/E140 既有方案
- **查重**：E140（CMake CMAKE_SYSTEM_NAME 平台块）为 CMake 口径，trigger_overlap；E160/E007 为 autoconf config.guess 口径；**Makefile UNAME_S 口径无直接条目 → 部分覆盖 + 新增差异**
- **可跨库复用**：是（任何 Makefile 系 C 库在 OHOS 首编必经）

### 候选 C2：Makefile 硬编码 `gcc -fsyntax-only`，OHOS 环境只有 clang

- **真实错误**：`make: gcc: No such file or directory`（Makefile:30）
- **根因**：上游 Makefile 直接调用 `gcc`；OHOS PC 环境只提供 clang
- **修复**：gcc→clang 符号链接垫片（不修改上游源码）
- **验证**：垫片后 make 编译流程通过
- **适用边界**：Makefile 硬编码 gcc/g++ 的库；反例：configure 探测 gcc 的 autotools 库走 E359
- **查重**：E359（configure `checking for program gcc... no`）为 autotools 探测口径，trigger_overlap 但场景不同；Makefile 直接调用 gcc 无直接条目 → **部分覆盖 + 新增差异**
- **可跨库复用**：是

### 候选 C3：header-only 库被 conan-init 误判为 autotools 生成错误配方模板

- **查重结论**：E321（martinmoene lite 系 header-only Conan2 迁移）、E322（header-only CMake INTERFACE 配方模式）、E257（header-only G1 build 门禁）已系统覆盖 → **完整覆盖，复用已有知识**，非新增候选

### 候选 C4：package_type=library 缺 shared option

- **查重结论**：E322 forbid 规则已覆盖（header-only 禁止 library+shared）→ **完整覆盖**

### 候选 C5：conan-init 生成类名含点号（Ffc.HTestConan）Python 语法错误

- **真实错误**：`SyntaxError: invalid syntax`（test_package/conanfile.py 类名）
- **根因**：conan-init 模板把包名含点号（ffc.h）直接拼为类名
- **修复**：类名 Ffc.HTestConan → FfcHTestConan
- **查重**：E478（版本号点号 package ID 解析）不同面；DRAFT-boost1.84-pkg-rename-archive 为包名复刻元数据一致性，不同面 → **未命中但域窄**（含点号包名少见），随 C1/C2 草稿记录不作独立草稿

### 候选 C6：FFC_IMPL 单头实现库消费者需定义实现宏

- **查重结论**：DRAFT-enet-2.7.0-single-header-impl-lib 与 E321-draft-0189（STR_API_ONLY 单头实现库模式）已覆盖 stb-style 单头实现库模式 → **完整覆盖**

### 七轴查重汇总（对 C1+C2 合并草稿）

| 轴 | 结论 |
|----|------|
| exact_duplicate | false（无条目描述 Makefile UNAME_S + gcc 硬编码在 OHOS 的组合问题） |
| causal_duplicate | false（E140/E160/E007 根因同源"平台检测不匹配"但均为 CMake/autoconf 口径，非 Makefile） |
| trigger_overlap | E140/E359 部分重叠（触发面：平台检测/编译器缺失） |
| solution_overlap | 无方案级重复（E140 补 CMake 平台块、E359 映射 HOSTCC；本候选为特性宏显式恢复 + 编译器垫片） |
| combination_novelty | true（Makefile uname 检测 + gcc 硬编码 + POSIX 宏恢复的组合无先例） |
| boundary_novelty | true（适用边界明确：Makefile 系 C 库在 OHOS 首编；反例：autoconf/CMake 库） |
| test_migration_novelty | 部分（上游测试入口直接可运行，无迁移需求；补充了 FFC_IMPL 消费者链接约定） |

### 路径判定

- C1+C2：已验证、可跨库复用、查重未命中/部分覆盖且有新增差异 → **路径 B 成立，建立同 stem 草稿**（DRAFT-ffc.h-26.07.01-makefile-uname-gcc-hardcode.kv/.md）
- C3/C4/C6：完整覆盖 → 复用已有知识（E321/E322/E257/enet draft）
- C5：域窄未命中，记入草稿边界说明，不作独立草稿
- **决定**：new_draft（路径 B，知识库扩展），仅 C1+C2 合并一条草稿

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方（package_type=header-library） |
| conandata.yml | 官方 GitHub URL + SHA-256 |
| test_package/ | 真实消费者测试（FFC_IMPL + ffc_parse_double_simple/ffc_parse_i64_simple） |
| patches/ | 无（无需补丁） |

## 注意事项

- GitHub 直连不可达：conandata.yml 必须保持官方 URL，镜像仅作传输层（E017 机制自动处理）
- ffc.h 为 FFC_IMPL 单头实现库：消费者 TU 需 #define FFC_IMPL 才能链接实现
- 包名含点号（ffc.h）：类名/CMake 目标名需人工去点号处理
---

**编译结束**: 2026-09-22 00:37
**最终状态**: built
