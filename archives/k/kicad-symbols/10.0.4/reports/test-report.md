# test-report.md — kicad-symbols 10.0.4（HarmonyOS PC 适配）

> 归档路径：`archives/k/kicad-symbols/10.0.4`
> 上游：<https://gitlab.com/kicad/libraries/kicad-symbols> tag `10.0.4`
> 源码 sha256：`f7f5653dc2f87d816ef5af6895f7339281eeb2e42c9a0984c4f4da69d3447c0c`

## 0. 包性质（重要，影响“编译/测试”口径）

上游 tag 10.0.4 的实测形态：

| 项 | 实测值 | 证据 |
|---|---|---|
| 顶层构建声明 | `project( kicad-symbols NONE )` | 上游 `CMakeLists.txt`（NONE = 不启用任何编译语言） |
| C/C++ 源文件 | **0 个** | `tar tzf` 共 23012 个条目：222 个 `*.kicad_symdir/` 目录、`Simulation_SPICE.sp`、`sym-lib-table`、`CMakeLists.txt`、`tools/kicad_lib_pack.py`、文档 |
| 唯一构建动作 | 运行 `tools/kicad_lib_pack.py`（Python）把 222 个 `.kicad_symdir` 打包成 222 个单文件 `.kicad_sym` 并改写库表 | 上游 `CMakeLists.txt` 的 `pack_all_libraries()` + `pack_symbols` 目标 |
| 发行版口径 | Debian `kicad-symbols` 10.0.6-1 为 `Architecture: all`，安装 `usr/share/kicad/symbols/*.kicad_sym` + `usr/share/kicad/template/sym-lib-table` | `dpkg-deb -c kicad-symbols_10.0.6-1_all.deb` |

因此本任务（平台标注 `lang=cpp`）**没有可编译的 C/C++ 目标**；“编译状态：通过”在本报告中
指**上游构建系统（CMake + 上游打包脚本）端到端成功执行并产出可被 KiCad 消费的完整资源包**。

## 1. 本地验证环境与方法

| 项 | 值 |
|---|---|
| 环境 | WSL2 Ubuntu 22.04 (x86_64)，与 CI 同源的 Conan 2.29.1 |
| 工具链 | Python 3.10.12 / CMake 3.22.1 |
| 命令 | `conan create . -pr:h=default -pr:b=default`（本地原生 profile；CI 用 `ci/conan/profiles/ohos-aarch64`） |
| 退出码 | **0**（含 `test_package` 全阶段） |
| 日志 | `.task-kicad/w3-conan-create.log`（本地） |

> 本地用原生 profile 而非 OHOS profile 是充分的：上游 `project(... NONE)` 不调用任何
> 编译器，OHOS 与原生构建执行的是同一条 CMake → Python 打包路径，产物按内容（sha256）
> 完全相同，不含任何架构相关产物。

## 2. 构建结果

```
kicad-symbols/10.0.4: RUN: cmake --install "…/build/Release" --prefix "…/p"
kicad-symbols/10.0.4: Package '24085be3dae734011e3c44cb8bf47131e967dbac' created
INFO:root:Updated symbol library table …/build/Release/packed/sym-lib-table with new packed library paths (222 updates).
```

| 产物 | 实测 |
|---|---|
| `share/kicad/symbols/*.kicad_sym` | **222** 个（上游 222 个 `.kicad_symdir` 一一对应） |
| `share/kicad/symbols/Simulation_SPICE.sp` | 1 个 |
| `share/kicad/template/sym-lib-table` | 33741 字节，222 条 `(lib …)`，uri 全部改写为 `…kicad_sym` |
| `licenses/LICENSE.md` | 2101 字节（CC-BY-SA-4.0 + 库例外条款） |
| 包体大小 | 221 MB（解压后；上游源码 tarball 11.9 MB 压缩） |
| 产物布局 | 与 Debian 官方 `kicad-symbols` 包一致 |

## 3. test_package 真实执行结果（26/26）

```
kicad-symbols/10.0.4 (test package): RUN: python3 -B "…/test_package/test_kicad_symbols.py" "…/p"
[1] installed layout
  [OK]   share/kicad/symbols exists
  [OK]   share/kicad/template/sym-lib-table exists
  [OK]   licenses/LICENSE.md shipped
  [OK]   packed symbol libraries present — 222 libs
  [OK]   Simulation_SPICE.sp installed — Simulation_SPICE.sp
[2] upstream check_lib_table.py checks
  [OK]   table parsed — 222 entries
  [OK]   Library table bad lines — 0 unparsable (lib ...) lines
  [OK]   Path separators
  [OK]   Incorrect nickname
  [OK]   all table uris point at packed .kicad_sym
  [OK]   Extra library
  [OK]   Missing library
  [OK]   Duplicated library
  [OK]   Every table uri resolves inside the package
[3] packed library structural integrity
  [OK]   every library has (kicad_symbol_lib ...) header
  [OK]   every library has balanced parentheses (quote-aware)
  [OK]   no empty library
  [OK]   total symbol count — 22776 symbols
[4] KiCad consumption semantics
  [OK]   Device:R has Reference/Value properties
  [OK]   Device:R pin count — expected 2, found 2
  [OK]   Device:C has Reference/Value properties
  [OK]   Device:C pin count — expected 2, found 2
  [OK]   power:GND has Reference/Value properties
  [OK]   power:GND pin count — expected 1, found 1
  [OK]   74xx:74LS00 has Reference/Value properties
  [OK]   74xx:74LS00 pin count — expected 26, found 26

kicad-symbols consumer test: 26/26 assertions passed
RESULT: PASSED
```

## 4. R34 负向验证（测试确实依赖被测包）

把包负载移走/替换为空壳后，同一测试脚本必须失败。为避开 221 MB 跨文件系统搬运，
负向验证用“桩包目录”实现（与原包共用同一份 `test_kicad_symbols.py`）：

| 场景 | 构造 | 结果 |
|---|---|---|
| 基线 | 真实包目录 | exit **0**，26/26 PASS |
| A. 负载完全缺失 | 空目录作为 package_folder | exit **1**，`RESULT: FAILED (package layout incomplete)`（FAIL: share/kicad/symbols / sym-lib-table / LICENSE.md） |
| B. 只有布局与库表、没有任何库文件 | 复制 `sym-lib-table` + `licenses/`，`symbols/` 留空 | exit **1**，**13/22** PASS（FAIL: packed libraries present / Extra library / Missing library / total symbol count 0 / 4 个已知库不存在） |
| C. 单个库文件被截断 | `power.kicad_sym` 只写一行未闭合的 `(kicad_symbol_lib (version 20231120)` | exit **1**，**16/24** PASS（FAIL: balanced parentheses / no empty library / power:GND present / …） |
| 恢复 | 真实包目录 | exit **0**，26/26 PASS |

即测试的每一条断言都建立在**真实读取包内 222 个库文件与库表**之上，不是空壳打印。

> CI 的 L1e（破坏性反向验证）只搬走 `bin/`、`lib/`、`include/`：本包为资源型包，
> 不含这三个目录，因此 CI 会打印 `[skip] L1e: No standard artifact dirs found to
> sabotage`；上面的 A/B/C 即该验证在本包形态下的等价替代证据。

## 5. 上游测试用例的处置

上游 `kicad-symbols` **仓库内没有任何测试程序**（无 `make check`、无 `ctest`、无
`meson test`）；上游把全部校验放在**另一个仓库** `kicad-library-utils`，由
`.gitlab-ci.yml` 的 `klc-check` 作业调用：

| 上游测试程序 | 作用 | 本 PR 处置 |
|---|---|---|
| `klc-check/check_lib_table.py` | 库表 ↔ 库文件集合一致性（6 类检查：Path separators / Incorrect nickname / Extra library / Duplicated library / Missing library / Library table bad lines） | **等价复现**：`test_package/test_kicad_symbols.py` 第 [2] 节用同名检查逐条实现，随每次 `conan create` 在 CI 真实执行（9 条断言，全过） |
| `klc-check/comparelibs.py` | KLC 规则检查 + 与上一版本符号库对比（`--check --check-derived --footprint_directory`） | **未纳入**：需要 git 历史（对比 base SHA 的库内容）并 `git clone kicad-footprints`，离线 CI 无法复现 |
| `.gitlab-ci.yml` `visual_diff` 作业 | 用 `kicad/kicad:nightly` 容器渲染符号差异图 | **未纳入**：需要 KiCad 容器与 GUI 渲染栈，与适配目标无关（上游 `allow_failure: true`） |

**未直接复制 kicad-library-utils 源码进 `test_package/` 的原因**：`check_lib_table.py`
的运行依赖链为 `junit.py → common/rulebase.py → common/print_color.py`（该仓库为
GPL-3.0 系），整体内联进本仓库（Apache-2.0）会引入许可与后续维护问题；因此选择
“逐条对照上游检查名做等价复现”，既保留可回归性，又不引入第三方代码。

**未覆盖风险（如实声明）**：`comparelibs.py` 的 KLC 规则检查（引脚命名、引脚类型、
图形规范等）在本 PR 中未执行；本 PR 只保证**结构完整性 + 库表一致性 + 关键器件可读性**。
若后续需要，可在获得网络与 git 历史的独立流水线中补充该检查。

## 6. 门禁自检（本地同构）

| 门禁 | 检查 | 结果 |
|---|---|---|
| L0a–L0e | `test_package/`、`conanfile.py`、测试源（`.py`）、`test()`+`self.run()`、`MANIFEST.yml` | ✅ 齐备 |
| L0k（R38） | 是否含 CLI 工具（`package_type=="application"` / bindirs / `RUNTIME DESTINATION bin`） | ✅ 均不命中（`package_type="unknown"`，无 bin/ 安装） |
| L0p | `settings` 含 os/compiler/build_type/arch | ✅ 四项齐备 |
| L0q | patches 声明与 `exports_sources` 一致性 | ✅ 无补丁，不触发 |
| L0o | 禁止在 `build()` 用 curl/wget 下载 | ✅ 源码由 `tools.files.get()` 经 conandata 获取 |
| L0i（R36） | 依赖必须已发布到制品仓 | ✅ `requirements()` 为空（无依赖） |
| L0j（R37） | 版本号占用 | 首次适配，版本号即上游 `10.0.4`，无后缀 |
| L0m | 目录名 = conanfile `name`，且为 conan slug | ✅ `k/kicad-symbols/10.0.4` |
| L0n | 分支名 `feat/<name>-<version>` | ✅ `feat/kicad-symbols-10.0.4` |
| L1a/L1b/L1d | `conan create` 进入 test 阶段、有真实执行痕迹、非 echo/print 假测试 | ✅ 见第 3 节 |
| L1e | 破坏性反向验证 | ⏭️ CI 会 skip（无 bin/lib/include）；等价证据见第 4 节 |
| L2 | `--version/--help` 冒烟 | ⏭️ 无 bin/，不适用 |
