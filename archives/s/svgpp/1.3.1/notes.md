# svgpp 1.3.1 适配笔记

## 一句话结论

路径 A（纯 header-only 配方，零补丁、零源码修改）。svgpp 自身不产出二进制，但**公开头文件
依赖 Boost**（含 Spirit/Qi），因此配方 `requires("boost/1.90.0", transitive_headers=True)`；
上游自带 GoogleTest 套件（单二进制 `ParserGTest`）在本机真跑，数字见下。

## 编译环境

- 构建系统：header-only。上游 `INSTALL` 原文（实测读取）：
  "As SVG++ is a header-only library, no installation is required. Just add path to
  'include' subfolder to your project include dirs."
- 编译器：clang 15.0.4（profile `ci/conan/profiles/ohos-aarch64`，
  `tools.build:compiler_executables=/data/service/hnp/bin/clang(++)`）
- 设备：鸿蒙 PC（OHOS 6.0 / armv8-aarch64），私有 `CONAN_HOME=~/tmp/ch/home-zhuli5-svgpp`
- 源码：`https://github.com/svgpp/svgpp/archive/refs/tags/v1.3.1.tar.gz`
  SHA-256 `be8a89df72d01cf062cc9815dd64c9576b4d20910d6d7aee7f0ea26484dc5e76`（本机对下载包实测计算）

## 上游源码清点（实测）

| 项 | 值 | 取证命令 |
|---|---|---|
| 包根内容 | `INSTALL LICENSE_1_0.txt README.md azure-pipelines.yml doc/ include/ src/ third_party/` | `tar tzf svgpp-1.3.1.tar.gz` 深度 2 |
| `include/` 扩展名分布 | 173 `.hpp` + 18 `.inc` + 1 `.md` | `find include -type f \| sed 's\|.*\\\\.\\\\\|\|' \| sort \| uniq -c` |
| 顶层目录 | `include/svgpp`（173 hpp）、`include/exboost`（上游内置 boost.parameter 派生头）、`src/{test,samples,demo,build}`、`third_party/{agg,googletest,rapidxml_ns,stb}` | 同上 |
| 引用 Boost 的公开头数量 | 79（`grep -rl 'include <boost' include/svgpp \| wc -l`） | 实测 |
| Boost 子模块用量 | mpl 76 / preprocessor 32 / spirit 23 / noncopyable 17 / range 12 / phoenix 12 / type_traits 11 / gil 11 … | 实测（`grep -rho '#include <boost[^>]*>' include`） |
| 上游测试目标 | 单二进制 `ParserGTest`（22 个测试 TU + 内嵌 gtest/gmock 源码，`target_link_libraries(... pthread)`）；另有 `CheckHeadersAutonomy`（每头一个 `#include` 的静态库，编译期自治检查）与 `FullParseTest`（自带 `main()`、需命令行传入 SVG 文件，属解析基准工具而非测试套件） | `src/test/CMakeLists.txt` 实读 |
| 上游 CI 口径 | `cmake -DCMAKE_BUILD_TYPE=Release -DBOOST_ROOT=<boost> ../src` → `make` → 运行 `build/bin/ParserGTest` | `azure-pipelines.yml` 实读 |
| 上游被注释掉的测试 TU | `path_adapter_test.cpp`、`supported_value_parsers_test.cpp`（上游自己从 ParserGTest 源列表中注释） | `src/test/CMakeLists.txt` 实读 |

## 关键适配点（每条都有盘上证据）

1. **`init-build` 的"嵌套源码提升"会把 Sphinx 文档目录当源码根并删除真实源码**（框架缺陷，本单实测命中）
   - 症状：`init-build` 日志打印 `嵌套源码检测: 找到源码在 doc/sphinx，正在提升到 svgpp-1.3.1.orig`，
     随后 `~/builds/svgpp-1.3.1.orig/` 只剩 `.rst`/`conf.py`/`Makefile`，`include/ src/ third_party/` 全部消失。
   - 根因（读码 `scripts/ohc/init_build.py:203-283`）：`_BUILD_MARKERS = ("configure","CMakeLists.txt","Makefile","meson.build")`；
     `_promote_nested_source()` 只在**根目录无 marker** 时触发，DFS 取**第一个**含 marker 的子目录，
     把该子目录内容提到根、然后 `shutil.rmtree` **删除其余全部条目**。svgpp 的 tag 包根只有
     INSTALL/LICENSE/README/azure-pipelines.yml ⇒ 按 sorted 顺序先命中 `doc/sphinx`（其内有 Makefile 与 CMakeLists.txt）。
   - 处置：`tar xzf … --strip-components=1` 手工重建 `.orig` 并 `cp -a` 出 `.work`
     （脚本 `~/tmp/uc2/z5-svgpp-fix.sh`，传输 md5 `d662ece30b0996fd28644378cc32143e`）；
     被误提升的文档树**未删除**，保留为 `~/builds/svgpp-1.3.1.{orig,work}.badpromote-20260923` 供复核。
   - 边界：**不再跑 `init-build --force` 或 `build --resume-from=Step1`**——同一代码路径会再次删。
     影响面（推断，未系统实测）：凡"包根无构建 marker、子目录有 marker"的包都可能命中，header-only 包尤其常见。
2. `ohc-run.py build svgpp 1.3.1`（一键驱动）在 Step3 以 `unknown_build_system` 出 HANDOFF、RC=2
   （日志行 68-74：`构建系统: unknown` / `❌ 无法检测构建系统`）。这是 header-only 在模式 A 下的正常出口，
   按其 SKILL §1.1 说明改走模式 B 的 `conan-init → conan-verify → finish`。
3. `conan-init` 按 `.build-context` 里被误判的 `BUILD_SYSTEM="autotools"` 生成了 Autotools 草稿
   （带 `autotools.configure()`/`make -j1` 和 `sha256: REPLACE_WITH_ACTUAL_SHA256` 占位符），
   已整体替换为 `templates/conanfile-headeronly.py.tmpl`（变体 A：header-only 库），
   结构对齐已入库先例 `archives/b/burst/3.1.1`（同为"header-only + 需要 Boost 头 + 跑上游测试"）
   与 `archives/b/bitsery/5.2.5`。
4. **Boost 是公开依赖而非测试依赖**：79 个公开头 `#include <boost/…>`（Spirit/Qi、MPL、Phoenix、Range、Fusion），
   故写进 `requirements()` 而不是 `test_requires()`，并在 `package_info()` 里
   `self.cpp_info.requires = ["boost::boost"]`；否则消费者连 `#include <svgpp/parser/grammar/path_data.hpp>` 都编不过。
   依赖可用性按 R35 用 `conan graph info --requires=boost/1.90.0 --build=never -pr:h=ohos-aarch64` 实测：
   `binary: Download`（即 OHOS armv8 二进制在 `ohpcd` 制品仓可直取，不需要源码编译）。
5. 打包集合必须同时含 `include/svgpp/**` 与 `include/exboost/**`（公开头直接引用后者），
   且 `include/` 下除 `.hpp` 外还有 18 个 `.inc` ⇒ `copy` 取 `*.hpp` 与 `*.inc`。
   （"漏装 `.inc` 会导致编译失败"属**预防性**判断，未做单独反证实验；`.hpp/.inc` 全集已由 test_package 与上游套件实测覆盖。）
6. `package_id()` 用 `self.info.clear()`：纯头文件包与 os/compiler/arch 无关（模板变体 A 规定）。
   配方内**不含任何 `settings.os` 平台分支**，故 R32（`in ("Linux","OHOS")`）无适用点。
7. **不产出 `commands.json`**：包内无 `bin/`（`cpp_info.bindirs = []`），R38/L0k/PF8 口径下纯库包必须无。
8. 上游测试的构建方式：**不改上游任何 CMake/源码**。`src/test/CMakeLists.txt` 自身不调用
   `find_package(Boost)`（Boost include 原本由父级 `src/CMakeLists.txt` 提供），而父级还会
   `add_subdirectory(demo/render)`（要编 agg）并在 CMake 4.x 下 `find_package(Boost REQUIRED)` 不可用；
   因此以 `cmake -S src/test` 独立配置，用 `-DCMAKE_PROJECT_INCLUDE=<注入文件>` 追加
   `include_directories(<svgpp include> <third_party> <boost include>)` 与 `-pthread`
   （`if (UNIX)` 在 OHOS 下不成立，pthread 需自带）。
9. `cmake_minimum_required (VERSION 2.8)` 被本机 CMake 4.1.2 直接拒绝 ⇒
   `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（实测必要；未改上游文件）。

## 已试过的失败方案

| 方案 | 结果 | 证据 |
|---|---|---|
| 用 `ohc-run.py search-url` 给出的 `https://download.savannah.nongnu.org/releases/svgpp/svgpp-1.3.1.tar.gz` | 302 → `nongnu.niranjan.co` → **404**，包根本不存在 | `curl -sIL` 实测 |
| `ohc-run.py build svgpp 1.3.1`（模式 A 一键） | Step3 `unknown_build_system`，RC=2 | `~/tmp/uc2/z5-svgpp-upstream/logs/gate3-build.log` 行 68-88 |
| 直接 `cmake -S src`（上游父 CMakeLists） | **未执行**：读码确认其 `find_package(Boost REQUIRED)` + `add_subdirectory(demo/render)`（agg）会引入无关重编译，改走第 8 条 | 判断依据 `src/CMakeLists.txt` 实读，属**预防性**规避 |
| `init-build --force` 重建源码树 | **未执行**：命中第 1 条同一删除路径，风险大于收益 | 依据 `scripts/ohc/init_build.py:264-276`，属**预防性** |

## 依赖版本

| 依赖 | 版本 | 形态 | 说明 |
|---|---|---|---|
| boost | 1.90.0 | requires（transitive_headers） | 公开头依赖；OHOS armv8 二进制 `binary: Download` |
| （GoogleTest/GoogleMock） | 上游内嵌 `third_party/googletest` | 仅上游测试构建使用 | 不进配方依赖 |
| expat / pugixml / rapidxml_ns | 不依赖 | — | XML 后端由使用者自带，见"适用边界" |

## 验证结果

**门禁 1-3 已跑；门禁 4/5（conan-verify / finish→W3 conan create）与上游套件实测被设备内存门槛挡住，未执行。**

| 门禁 | 命令 | RC | 证据 |
|---|---|---|---|
| 1 W0 预检 | `bash ci/scripts/preflight_check.sh svgpp/1.3.1` | **0** | 输出 `预检通过（无依赖需要检查）`（当时配方未生成，依赖需在 boost 落地后复检） |
| 2 配方检索 | `python3 scripts/ohc-run.py recipe-search svgpp` | **0** | `无相似配方（语料 6214 条）`；按构建系统检索 `-b headeronly` 命中 3 条数据/脚本类包（非 C++ 库） |
| 3 一键驱动 | `python3 scripts/ohc-run.py build svgpp 1.3.1` | **2** | `~/tmp/uc2/z5-svgpp-upstream/logs/gate3-build.log` 行 68-88：`构建系统: unknown` → `❌ 无法检测构建系统` → HANDOFF `EXIT_REASON: unknown_build_system` `STEP_FAILED: Step3`（header-only 的正常出口，见上文第 2 条） |
| 4 conan-verify | `python3 scripts/ohc-run.py conan-verify svgpp 1.3.1` | **未执行** | 设备内存门槛 `~/tmp/uc2/gate.sh` 连续 8+ 次 `GATE_FAIL: MemAvailable≈5.5GB < 6000MB`（load≈20，他窗在构建）；按要求不抬高门槛、不硬起、不动他人进程 |
| 5 finish(W3) | `python3 scripts/ohc-run.py finish svgpp 1.3.1 built` | **未执行** | 同上 |
| W4 审计 | `pre_pr_audit.py generate` → 审计输入 JSON；`check` | generate **0** | `~/tmp/uc2/z5-svgpp-upstream/audit-input-svgpp-1.3.1.json`（2213597 字节）待独立审计代理出报告；`check` 当前只报 `.ci-result.json` 缺失（W3 未跑，属预期） |

已实测到的依赖前提（不需要构建设备槽）：`boost/1.90.0` 在 `ohpcd` 制品仓有 OHOS armv8 二进制
（`conan graph info --requires=boost/1.90.0 --build=never -pr:h=ci/conan/profiles/ohos-aarch64`
→ `binary: Download`；未使用被禁止的 `conan list` 判据，R35）。

待补：test_package 的 `checks=23`（静态计数，源码内 `CHECK/CHECK_NEAR` 宏 23 处，运行时会打印
`checks=<n> failures=<m>` 自证）与上游 `ParserGTest` 的实测用例数，都必须由真机运行回填；
**未取得实测值前不写入 `test_package/MANIFEST.yml`**（该文件仍是 conan-init 生成的待填骨架，未入库）。


## 适用边界

- 仅覆盖 1.3.1；若上游变更 `include/` 布局（尤其新增 `.inc`/其它扩展名或去掉 `exboost`），打包 `copy` 模式需复核。
- **不 require 任何 XML 解析库**：svgpp 的 XML 后端是策略（`include/svgpp/policy/xml/*`），
  由使用者自带 expat/pugixml/rapidxml 等；本包只发布头文件。
  上游自己的头文件自治检查也刻意排除该目录（`src/test/CMakeLists.txt`：
  `if (NOT ${i} MATCHES "policy/xml/.*")`）——本配方未单独编译 `policy/xml/*`，与上游口径一致。
- `src/demo/render`（需 agg）与 `src/samples`（需 expat/xerces 等后端）**不在**本配方构建范围内：
  它们演示"用哪种 XML 后端"，与库的可安装性无关；未构建（如实声明，不当作失败）。
---

## 静态段补做（2026-09-23 晚，接手窗只做静态/非构建，未启动任何编译）

### A. G1 三项已补齐（本窗唯一的配方改动）

`archives/s/svgpp/1.3.1/conanfile.py`：
- import 扩为 `apply_conandata_patches, copy, export_conandata_patches, get`；
- 新增 `export_sources()` → `export_conandata_patches(self)`；
- 用真实 `build()` 取代原「刻意不定义 build()」注释块，函数体**只有** `apply_conandata_patches(self)`；
  顺带去掉该注释里对并不存在的 `reports/upstream-tests.md` 的引用（不留空头承诺）。

**为什么这不等于"塞假补丁"**：G1 是**字面量**检查——`scripts/ohc/conan_verify.py:480-497` 逐条判
`"def build("` / `"export_sources"` / `"apply_conandata_patches"` 是否出现在 conanfile 文本里；
而 `templates/conanfile-headeronly.py.tmpl` 变体 A 写的是"无编译阶段：不定义 build()，或留空"
⇒ **模板原文过不了 G1**（框架张力，本窗不动框架）。本窗取"只调 conan 标准补丁钩子、不新增任何补丁文件"：
`patches/` 仍是空目录、`conandata.yml` 仍是 `patches: {}`，该组合是**读码确认的 no-op**——
`~/.local/lib/python3.14/site-packages/conan/tools/files/patches.py:90-100`（dict 分支
`patches.get("1.3.1", [])` → 空列表，不告警不抛异常）与 `:127-141`（export 同理）。
写法对齐已入库先例 `archives/b/burst/3.1.1/conanfile.py`（burst 的 `build()` 另有 CMake，因为它把
doctest 套件跑在 build() 内；svgpp 的上游套件按上文关键适配点 8/9 在配方外构建，见 D 段）。

### B. `ohc-run.py build` RC=2「无法检测构建系统」根因（读码 + 盘上清单双向确认）

- 判据：`scripts/ohc/driver.py:723-737` `_detect_build_system()` **只看 `build_src_dir` 根目录**的
  `CMakeLists.txt` / `meson.build` / `Makefile.PL` / `Build.PL` / `setup.py` / `pyproject.toml` /
  `configure(.ac|.in)` / `Makefile` / `GNUmakefile`，全不命中即 `return "unknown"`
  → `driver.py:890` 打 `❌ 无法检测构建系统` → HANDOFF
  `EXIT_REASON: unknown_build_system`、`EXIT_CODE: 2 (resumable)`、`STEP_FAILED: Step3`
  （`~/tmp/uc2/z5-svgpp-upstream/logs/gate3-build.log` 行 68-88 原文一致）。
- 上游 tag 包根实测内容：`INSTALL  LICENSE_1_0.txt  README.md  azure-pipelines.yml  .gitignore  doc/  include/  src/  third_party/`
  （`ls ~/builds/svgpp-1.3.1.orig` 与 `tar tzf ~/builds/svgpp-1.3.1.tar.gz` 深度 3 双向核对）。
  唯一的 CMake 工程文件在**嵌套**的 `src/CMakeLists.txt`，检测器不下钻 ⇒ "unknown"。
- 定性：**header-only 包在模式 A 一键驱动下 RC=2 是设计内出口**（SKILL §1.1 要求此类包走模式 B
  `conan-init → conan-verify → finish`），不是配方缺陷、不是 OHOS 工具链问题、不是依赖问题。
  它与"关键适配点 1"的 `init-build` 误提升同形状：**包根无 marker、子目录有 marker**。

### C. 本窗静态校验（全部零构建，实测 RC；日志在 `~/tmp/uc2/z5-s-static-*.log`）

| 检查 | 命令 | 结果 |
|---|---|---|
| 配方语法 | `python3 -m py_compile archives/s/svgpp/1.3.1/conanfile.py` | **RC=0** |
| W0 预检 | `bash ci/scripts/preflight_check.sh svgpp/1.3.1` | **RC=0**，`所有依赖均已发布到制品仓` |
| 配方检索 | `ohc-run.py recipe-search svgpp` | **RC=0**，`无相似配方（语料 6214 条）` |
| 知识图谱 | `ohc-run.py graph validate` | **RC=0**（540 条，无一致性错误） |
| R47 语言预检 | `ohc-run.py lang-preflight svgpp 1.3.1 --src ~/builds/svgpp-1.3.1.orig` | **RC=0**，milestone=`lang_checked`；草稿经 `OHC_RESULT_OUT` 显式改道到 `~/tmp/uc2/z5-svgpp-upstream/static-lang-result.json`，以免覆盖共享的 `$HOME/ohpcd-ai-worker-result.json` |
| YAML | `conandata.yml` / `manifest.yaml` | 均解析 OK |
| YAML | `test_package/MANIFEST.yml`（未入库骨架） | **ScannerError `line 23 col 16`**：`source: svgpp-1.3.1/<TODO: 测试源文件>` 里的 `: ` 撞 YAML，`assertion_count: <TODO: 断言数>` 同问题 ⇒ conan-init 生成的这份骨架**本身不是合法 YAML**，填数时必须整体改为带引号标量，否则任何解析它的门禁都会在 L0e 上炸 |
| 打包集合完整性 | `find include -type f` 扩展名分布：173 `.hpp` + 18 `.inc` + 1 `.md`（`include/exboost/README.md`） | `package()` 的 `*.hpp` + `*.inc` 覆盖全部 191 个头文件，无 `.h` 漏项 |

### D. 剩余项（必须占构建闸口，本窗按纪律未跑）

`conan-verify`（G1 应转绿、G2 conan create 首次实跑、G3/G4/L2/L4/L5）、`finish`（W2 结构 + R36 + W3 写 `.ci-result.json`）、
上游 `ParserGTest` 真机运行取五维数字 → 回填 `test_package/MANIFEST.yml`（顺带修好 C 段那条 YAML 缺陷）并入库、
W4 独立审计 P0/P1 清零、建 PR、`result.json` 绑最终 HEAD 后再 finish。**顺序保持"所有提交做完最后 finish"**。

### E. 框架隐患取证树仍在（只核实、未删未改）

`~/builds/svgpp-1.3.1.orig.badpromote-20260923` 与 `~/builds/svgpp-1.3.1.work.badpromote-20260923`
各 26 条目，内容为被误提升的 `doc/sphinx` 树（`.rst`/`conf.py`/`make.bat`/`Makefile`/`CMakeLists.txt`），
且两棵树里 `include/` 均 `No such file or directory` —— 即"删掉真实源码"的现场证据保持原样。


## G2→G4 转绿实测（2026-09-23 19:35–19:40，构建验证段子代理，占设备构建槽）

### 门禁结果：`ohc-run.py conan-verify svgpp 1.3.1` **RC=0，8 道门禁全 PASS**

| 门禁 | 结果 | 实际含义（不美化） |
|---|---|---|
| G0 预构建风险评估 | PASS | 构建系统 `unknown`（header-only 无根 marker）⇒ 跳过预查询 |
| G1 配方完整性 | PASS | 含 `export_sources()` / `build()` / 补丁钩子三项 + `test_package/` + `MANIFEST.yml` |
| G2 conan create | PASS | 干净源码下载→export→package→test_package **编译+链接+运行**全通过 |
| G3 系统同名库隔离 (R26) | PASS | 无 bin/、无 lib/ ⇒ 无冲突（纯头包） |
| G4 产物完整性 | PASS | ⚠ 实为「无法找到程序包 ID」的降级通过 |
| L2 / L4 / L5 | PASS | ⚠ 实为「跳过（无 cache 路径）」 |

证据：`archives/s/svgpp/1.3.1/reports/conan-verify-report.md`（`Verdict: PASS`，Date 2026-09-23T19:39:18）、
`reports/conan-create.log`、控制台日志 `/storage/Users/currentUser/tmp/uc2/svgpp/verify-fg.log`（`VERIFY_FG_RC=0`，
末行 `✅ 配方验证通过: svgpp 1.3.1`）。

**G4/L2/L4/L5 属「跳过式 PASS」的根因（框架正则缺陷，本窗不改框架）**：
`scripts/ohc/conan_verify.py:597-599` 用 `(\w+/\w+@\w+/\w+):(\w+)` 抓包 ID，而版本串 `1.3.1` 里的点不在 `\w` 内
⇒ 抓不到 `_package_id` ⇒ G3/G4/L* 拿不到 cache 路径。纯头包本就无二进制，L2(smoke)/L4(checksec)/L5(产物基线) 对本包 N/A，
但**这条跳过是正则造成的，不是设计判断**，留此备考。

### G2 首跑到转绿之间修掉的三条真实错误（按出现顺序）

1. **源下载被死镜像挡死**：`conan_verify` 的「E017 预防」把 `https://github.com` 改写成 `https://ghfast.top/https://github.com`；
   本窗实测该代理 `curl --max-time 60` **0 字节超时**，而同一时刻 github 直连 **6s / 200 / 3081722 B** 完成。
   ⇒ 处置：按机上既有 house 口径开 `core.sources:download_cache=/storage/Users/currentUser/tmp/ch/dlcache`（只写进**本任务私有** CONAN_HOME 的 global.conf），
   用 conan 自带的 `file://` 本地源口把**从 github 直连取回、sha256 与 `conandata.yml` 完全一致**（`be8a89df…4dc5e76`）的 tar 包喂进缓存；
   侧车 `dlcache/s/be8a89df….json` 记下镜像 URL ⇒ 门禁注入镜像 URL 时命中缓存、不再走网络。
   **交付的 `archives/.../conandata.yml` 为 git 里的官方 https 单 URL，未入库任何 `file://`**（PF7 无风险）。
   ⚠ 原表述"自始至终未被改写"不成立：该文件确曾被「预下载/镜像」改写，且收工代提交 `bf4fafeabe` 又把镜像优先的列表形态
   带回 HEAD；本轮（主理-11，W4-r1 P1-03）已按 `review_memory §13 R39` 复原为仅官方 https 单 URL。
   证据 `~/tmp/uc2/svgpp/{seed-002.log,gate-001.log,verify-002.log}`。
2. **消费者用例编译失败（clang `10 errors generated`）**：`test_svgpp.cpp` 把语法对象写成
   `path_data_grammar<...> grammar(boost::phoenix::ref(context));`，但两个 grammar 模板**只有默认构造函数**
   （`include/svgpp/parser/grammar/path_data.hpp:28`、`transform.hpp:26`），`boost::phoenix::ref(ctx)` 属于
   `phrase_parse` 的表达式位——上游 `src/test/path_grammar_test.cpp:31-32` 就是 `grammar;` + `grammar(phoenix::ref(ctx))` 的写法。
   另 `same_event()` 第 4 形参 `absolute` 无默认值，而 transform 段按 3 参调用。
   ⇒ 5 处构造改 `grammar;`；`same_event` 补 `= true`。
3. **断言假阳性（实测 `checks=20 failures=2`）**：case 2 的路径串以 `C` 起始。SVG 1.1 B.1 规定路径定义必须以 moveto 起始，
   svgpp 依此在起点即停止匹配（临时诊断实测 `consumed=0`、events=0）⇒ **用例写错，不是包缺陷、不是 OHOS/工具链问题**；
   改为 `M300,200 C… Q… a…` 并补 `move_to` 断言，复跑 `checks=24 failures=0`、`consumed=72/72`。

### 测试五维账本（本窗实测口径）

| 维度 | 数 | 来源与口径 |
|---|---|---|
| `N_static` 上游静态声明 | **52** | tag 1.3.1 `src/test/*.cpp` 逐项：`TEST(` 29 + `TEST_F(` 4 + `TEST_P(` 19（25 个测试 TU） |
| `N_registered` 纳入 ParserGTest 目标 | **50** | `src/test/CMakeLists.txt` 源列表实读；`path_adapter_test.cpp`、`supported_value_parsers_test.cpp` 各 1 个 `TEST` 被**上游自己**注释掉，不入目标 |
| `N_executed` 上游真机执行 | **0（未执行）** | 层 1 未集成进 `build()`；本窗未取得第二个构建槽去编 `ParserGTest`（23 测试 TU + 内嵌 gtest/gmock 3 TU，重模板）。19 个 `TEST_P` 配 19 处 `INSTANTIATE_TEST_SUITE_P`，参数展开后的真实运行数**只有真跑才有**，不拿静态数反填 |
| 未执行分类 | 50 项全归「配方外未构建」；另 2 项系上游自行注释（不入适配后分母）；`CheckHeadersAutonomy` 为编译期头自治检查、无运行期用例；`FullParseTest` 需命令行传 SVG 文件、属解析基准工具而非套件 | — |
| `N_consumer` 消费者测试 | **1 个程序 / 24 断言全通过**（`N_assertion`=24） | conan create 内实跑：`svgpp consumer test: checks=24 failures=0`；静态断言点 24 = 含 `CHECK` 的 26 行减 2 行 `#define` |

⚠ **留给主理/CIW 的决策点（不许本窗替它宣布通过）**：`手册/04` 与 `docs/TEST_QUALITY_SPEC.md` 的层 1 要求
「上游测试必须在配方 `build()` 中真实执行，0 执行一律不通过，无论理由」。本包 header-only、上游无 `make check`/ctest 注册，
若真要满足层 1，需在 `build()` 内用 CMake 构建并运行 `ParserGTest`（约 26 个重模板 TU，要独占构建槽 + 内存余量）。
本窗**没有**擅自改 `build()` 语义（前序窗已定「上游套件在配方外构建」），按实数记 0 执行 + 原因。

### 环境与踩坑留痕

- `CONAN_HOME=/storage/Users/currentUser/tmp/ch/home-zhuli5-svgpp`（复用 主理-5 的 home，含 ohpcd remote；新建 home 会把已发布的 boost 误判成未发布）。
- profile 给的 `-j20` 在 HMDFS 上会让 make jobserver 报 `mkfifo ...: Operation not permitted`（退化串行，不影响结果，只影响速度）。
- 内存门槛全程 `build-slot.sh --wait 60 --mem 6000`；`MemAvailable` 实测 5.9–6.7 GB 反复穿越门槛，`--mem` 是 fail-fast `exit 3` ⇒ 外层重试循环只对 `rc=3` 重试、其它失败立即停手（脚本 `~/tmp/uc2/svgpp/{seed.sh,gate.sh,verify.sh,iter.sh}`，日志同目录）。

### finish 副作用取证与处置（2026-09-23 19:48–19:55）

`finish svgpp 1.3.1 built` 的退出码是 **2（HANDOFF 态，`EXIT_REASON: finish_success`、banner 内 `EXIT_CODE: 0`）**，
**W3 权威判据已过**：`archives/s/svgpp/1.3.1/.ci-result.json` = `exit_code: 0` / `step: W3_local_ci` /
`integrity_hash: dc6664b246edf084` / `log_sha256: ae05fec1d40758b4…28238c8ea`（日志 `reports/w3-local-ci.log`）。
RC=2 来自第 6 步「知识整理 HANDOFF」提示，不是构建失败。

**两个必须人工拦掉的框架副作用**（本窗已清，未入库）：

1. `conanfile.py` 之外的 **`conandata.yml` 被「预下载/镜像」重写**成
   `url: [https://gh-proxy.com/https://github.com/…, https://github.com/…]`——镜像域名进正文会被 **PF7 源URL闸**
   与静态审查直接判违规。已用 finish 自己留下的 `conandata.yml.orig` 还原为**仅官方 https 单 URL**
   （还原后 `git diff` 对该文件为空），被改写的那份留档 `~/tmp/uc2/svgpp/conandata.mirror-rewritten.*.yml`。
   ⚠ 但收工代提交 `bf4fafeabe` 再次把列表形态带入 HEAD（正是下一段"若再跑 finish 污染会重现"的同类事故），
   本轮按 R39 复原为单官方 URL 后，本条结论才与盘上一致。
2. `finish` 第 [1/10] 步 `refresh-patch --auto` 用 `per-file-difflib` 比对
   `builds/svgpp-1.3.1.orig` ↔ `builds/svgpp-1.3.1.work`，**把框架自己写进工作源码树的
   `.pre-scan-report.yaml` 当成"上游源码改动"生成了补丁** `patches/0001-.pre-scan-report.yaml.patch`
   （57 行、`platform_only: True`、`guard: pending`、`patches_count: 1`），并在 `manifest.yaml` 追加
   `patch_generation:` / `patch_classification:` 两块。这属"假补丁"家族：`.pre-scan-report.yaml` 不是上游文件，
   补丁内容与 svgpp 源码无关。**已删补丁与备份目录、并删掉 manifest 那两个块**（留档
   `~/tmp/uc2/svgpp/junk-patch-evidence/`）；`patches/` 恢复空目录、`conandata.yml` 仍是 `patches: {}`。

⚠ **给后续窗口的提醒**：`manifest.yaml` 头部注释写明"由 finish 收尾时会复核/重写本文件"——
**若再跑一次 finish，上面两处污染会重新出现**，务必复查 `conandata.yml` 的 URL 与 `patches/` 内容后再提审。
另：`.ci-result.json` / `.build-closed` / `ci-metadata.json` 在本仓 `.gitignore` 内（第 213/238/247 行），
`git add archives/s/svgpp` 不会带上它们，submit/W4 需要时要按先例处理。

## 层 1 补做：上游 ParserGTest 进配方 build() 真跑（2026-09-23 20:00–21:3x，补做子代理 主理-9）

### 改动面（只动 conanfile.py + 三处账本；上游源码零修改、零新增补丁）

- `generate()`（新增）：把 `src/test` 需要的 include 目录写成
  `svgpp-upstream-test-inject.cmake`（构建树 `include`、`third_party`、
  boost 包 include 绝对路径——由 `self.dependencies["boost"].package_folder` 生成），
  再过 `CMakeToolchain`（有 ninja 则用 ninja）注入
  `CMAKE_POLICY_VERSION_MINIMUM=3.5`、`CMAKE_PROJECT_INCLUDE=<注入文件>`，
  并在 OHOS 下 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`
  （与已入库先例 `archives/b/burst/3.1.1` 同构；使 `UNIX` 成立，
  上游 `target_link_libraries(... pthread)` 分支与内嵌 gtest 按上游 CI 行为工作，
  编译器仍是 profile 的 OHOS clang）。
- `build()`：保留 `apply_conandata_patches(self)`，新增
  `cmake.configure(build_script_folder="src/test")` →
  `cmake.build(target="ParserGTest", -j4)`（make 兜底时追加 `--jobserver-style=pipe`，
  针对 HMDFS 拒绝 mkfifo 的既有踩坑）→ `self.run("<build>/ParserGTest
  --gtest_color=no --gtest_output=xml:parser_gtest.xml", env="conanrun")`。
- `test_package/` 保持不动；`package()/package_id()/package_info()` 不动。

### 带外实测（探测，先于 conan-verify，验证参数与耗时）

日志 `/storage/Users/currentUser/tmp/uc2/svgpp/probe/`（`probe.log`、
`gtest-list.txt`、`gtest-result.xml`、`gtest-run.log`、`probe.status`）：

| 步骤 | 结果 |
|---|---|
| configure（standalone src/test，Ninja，同配方参数） | RC=0（3s） |
| build ParserGTest（23 测试 TU + gtest/gmock 3 TU + 内嵌头，`-j4`） | RC=0，**139.9s**（`MEMCAP[run] ... rc=0 用时139.9s`；`peak=19MB` 是 0.5s 采样没抓到 clang 峰，不作证据） |
| `--gtest_list_tests` | 200 条 |
| 运行 ParserGTest | RC=0：`[==========] 200 tests from 30 test cases ran. (7 ms total)`、`[  PASSED  ] 200 tests.`；XML `tests=200 failures=0 disabled=0 errors=0` |

### 带内实测（层 1 装进配方后的 conan-verify）

- `python3 scripts/ohc-run.py conan-verify svgpp 1.3.1`：外层
  `build-slot.sh --wait 60 --mem 6000` 重试（try1–7 rc=3，闸区间 MemAvailable 5.1–6.0GB，
  **未降阈值、未用 memcap 通道**），**try=8 rc=0（21:03:08）**。
  日志 `/storage/Users/currentUser/tmp/uc2/svgpp/L1-conan-verify-8.log`
  （末行 JSON `milestone: conan_verify_passed`），状态文件 `L1-conan-verify.status`。
- **conan create 内部真跑了上游套件**（非 Cache 命中）：
  `reports/w3-local-ci.log`（共 855 行）：215 行 `RUN: cmake --build … --target ParserGTest -- -j20 -j4` → 216-241 共 26 个
  `Building CXX object` → 245 行 `Running main() from gmock_main.cc` → 739-740 行 `[==========] 200 tests from 30 test cases ran.`
  与 `[  PASSED  ] 200 tests.`；消费者断言 `svgpp consumer test: checks=24 failures=0` 在同文件 825 行。
  ⚠ 旧版此处误写为 `reports/conan-create.log 行 143–638`——该文件实测只有 138 行（21:22 被后一次 finish 覆盖），
  属引用失效（W4-r1 P1-02 整改），数字本身未变。
- G0–G4 全 PASS；G4/L2/L4/L5 仍为「无包 ID ⇒ 跳过式 PASS」（框架正则根因见上一节，未变）。

### 五维账本修订（本包最终口径，与 `manifest.yaml`、`test_package/MANIFEST.yml` 同源）

| 维度 | 数 | 口径 |
|---|---|---|
| `N_static` | 52 | TEST 29 + TEST_F 4 + TEST_P 19（宏，逐文件行首锚定复核过） |
| `N_registered` | 50 | 同上 −2（上游注释掉的 2 个 TEST） |
| `N_executed` | **200** | 用例（实例）数：非参数化 **35** + 参数化实例 **165** |
| 通过/失败/跳过/disabled | **200 / 0 / 0 / 0** | gtest 汇总行与 XML 双向一致 |
| `N_consumer` | 1 程序 / 24 断言全过 | 不变 |

`35 = 31 个注册非参数化宏 + 4`：`transform_strict_grammar_test.cpp` 全文只有
`#define SVGPP_STRICT_TRANSFORM_SEPARATOR` + `#include "transform_grammar_test.cpp"`，
把 4 个 TEST 以同名套件 `transform_grammar` 在"严格分隔符"模式下**再执行一遍**——
这就是注册宏数(50)与执行用例数(200)差异的三个叠加机制之一
（另两个：19 个 TEST_P 经 19 处 INSTANTIATE 展开为 165 实例；2 个 TU 被上游注释出目标）。
**50 个注册宏全部被执行覆盖，「注册未执行」清零**；`CheckHeadersAutonomy`（编译期自治
检查，无运行期用例）与 `FullParseTest`（需命令行传 SVG 文件的基准工具）不入用例分母，
前者**未**纳入 build()（约 150+ 个纯 include TU 的全量编译成本、且无运行期证据可入账），
理由已写进 `test_package/MANIFEST.yml`。

上一节「N_executed=0（未执行）」自本段起作废，由本段数字替代。
---

**编译结束**: 2026-09-23 21:22
**最终状态**: built

## 交付前口径对账（主理-11 · W4-r1 整改）

本文按时间顺序追加，**唯一有效申报口径 = 上文「五维账本修订（本包最终口径…）」段**：
`N_static`=52（TEST 29 + TEST_F 4 + TEST_P 19）/ `N_registered`=50 / `N_executed`=200（200 通过、0 失败、
0 跳过、0 disabled）/ `N_consumer`=1 个消费者程序、`N_assertion`=24。

以下更早小节里的过程记录**已过期，不得作为申报依据**（保留以留痕，故不删原文）：
1. 「门禁 4/5 conan-verify、finish(W3) 未执行」——两项其后均已真机跑过（conan-verify RC=0 于 19:35-19:40；
   W3 `.ci-result.json` `exit_code 0` 于 **21:25:24**，`integrity_hash 46b07b53da2d31e4` /
   `log_sha256 e53fe11a4345378e6eede82f4f8a3f8e5156aabe151422550e64f185c086e7a3` 为当前有效值）。
   同段与上文出现的 `integrity_hash dc6664b246edf084`、`log_sha256 ae05fec1d40758b4` 属 19:48 那次 finish 的结果，
   已被 21:25:24 这次取代，**不得引用**。
2. 「`checks=23`（静态估数）」——实测与交付口径均为 **24**（源码内含 `CHECK` 的 26 行减去 2 行 `#define`）。
3. 「22 个测试 TU」——上游 `src/test/CMakeLists.txt` 实读为 **23** 个纳入 `ParserGTest` 的测试 TU，
   加 3 个 vendored gtest/gmock TU 共 26 个编译对象，与 `w3-local-ci.log:216-241` 的 26 行 `Building CXX object` 一致。
   （`conanfile.py` 与 `test_package/` 本轮**一字未动**，故该失准只在此处统一纠正。）
4. 「`reports/conan-create.log` 行 143-638」——层 1 真机证据实际位置见本段上方引用整改，改指 `w3-local-ci.log`。
5. 源 URL 形态——HEAD 交付为**仅官方 https 单 URL**（R39），任何"镜像优先列表"的描述均不适用。
