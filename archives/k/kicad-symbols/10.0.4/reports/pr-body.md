## PR 信息
- **三方库名称**：kicad-symbols
- **上游版本**：10.0.4
- **上游仓库地址**：https://gitlab.com/kicad/libraries/kicad-symbols
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E255（resource-data-package-conan-recipe：资源型数据包配方模式与 L0 门禁关系）、E305（字体/资源型数据包的 test_package 验证方法）、E251（数据包打包先例）、技能 openharmony-compile-agent

> 源码包 URL（conandata.yml）：`https://gitlab.com/kicad/libraries/kicad-symbols/-/archive/10.0.4/kicad-symbols-10.0.4.tar.gz`
> （SHA-256: `f7f5653dc2f87d816ef5af6895f7339281eeb2e42c9a0984c4f4da69d3447c0c`）
> 上游官方 GitLab 按 tag 生成的归档；连续两次下载 sha256 一致，故固定校验和（R39）。
> 归档路径：`archives/k/kicad-symbols/10.0.4`

## ⚠️ 关于任务语言标签的重要说明（请先阅读）

平台任务 **#12840**（`kicad-symbols` / `10.0.4`）标注 `lang=cpp`，但**上游没有任何 C/C++ 代码**：

| 事实 | 证据 |
|---|---|
| 顶层构建声明为 `project( kicad-symbols NONE )`（NONE = 不启用任何编译语言） | 上游 tag 10.0.4 `CMakeLists.txt` |
| 仓库内 **0 个 C/C++ 源文件** | `tar tzf` 共 23012 条目：222 个 `*.kicad_symdir/` 目录 + `Simulation_SPICE.sp` + `sym-lib-table` + `CMakeLists.txt` + `tools/kicad_lib_pack.py` + 文档 |
| 唯一构建动作是用 Python 打包符号库 | 上游 `CMakeLists.txt` → `tools/kicad_lib_pack.py`（把 222 个 `.kicad_symdir` 合并为 222 个单文件 `.kicad_sym`，并改写库表） |
| 发行版口径 | Debian `kicad-symbols` 10.0.6-1 为 `Architecture: all`，安装 `usr/share/kicad/symbols/*.kicad_sym` + `usr/share/kicad/template/sym-lib-table`（实测 `dpkg-deb -c`） |

同批任务 `kicad-library`、`kicad-library-symbols`、`kicad-library-packages3d`、
`kicad-packages3d` 同样都是纯数据包，平台一律标 `lang=cpp` —— 可判断该 `lang` 字段是按
套件批量赋值的，并不代表包含 C++ 编译单元。

因此本 PR 按**上游真实形态**完成适配：交付一个与 Debian 官方包同构、可被 KiCad 直接
消费的符号库资源包（而不是伪造一个 C++ 目标或塞入无意义桩代码）。下文“编译状态：通过”
即指**上游构建系统（CMake + 上游官方打包脚本）端到端执行成功并产出完整、可校验的库数据**。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游仓库无单元测试框架、无 `make check` / 无 `ctest` / 无 `meson test`（顶层 CMakeLists 只有 `pack_symbols` 与 `install` 目标） |
| 集成测试 | 2 | 上游把全部校验放在**另一个仓库** `kicad-library-utils`，由 `kicad-symbols/.gitlab-ci.yml` 的 `klc-check` 作业调用：① `klc-check/check_lib_table.py`（库表 ↔ 库文件一致性，6 类检查）② `klc-check/comparelibs.py`（KLC 规则检查 + 与上一版本符号库对比） |
| 其他测试 | 1 | `.gitlab-ci.yml` 的 `visual_diff` 作业（`kicad/kicad:nightly` 容器渲染符号差异图，上游标记 `allow_failure: true`） |
| **合计** | **3** | 计算方式：检索上游 `CMakeLists.txt`（无测试目标）与 `.gitlab-ci.yml`（`klc-check` 作业 2 个程序 + `visual_diff` 作业 1 个），逐项计数 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试，本适配不引入新的单元测试框架 |
| 集成测试 | 1 | −1 | 上游 `check_lib_table.py` 的 **6 类判定逐条等价复现**（检查名与上游一一对应），随每次 `conan create` 在 CI 真实执行（9 条断言，全过）；`comparelibs.py` **未纳入**——它需要 git 历史（对比 base SHA 的库内容）并 `git clone kicad-footprints`，离线 CI 无法复现（详见 `reports/test-report.md` 第 5 节） |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/test_kicad_symbols.py`：消费者视角真实读取包内 **222 个打包库 + 库表**，校验安装布局、库表 uri 占位符解析、每个库文件的 s-expression 完整性与括号配平、22776 个符号总数、已知器件（`Device:R` / `Device:C` / `power:GND` / `74xx:74LS00`）存在且具备 `Reference`/`Value` 属性、引脚数正确（共 26 条断言） |
| **合计** | **2** | **−1** | 上游 3 项中：1 项等价复现并真实执行、1 项因需联网与 git 历史未纳入、1 项（容器渲染差异图）与适配目标无关未纳入；另新增 1 项鸿蒙侧消费者测试 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（无）

> 本 PR **没有**上游测试文件被修改或复制进仓库：`test_package/test_kicad_symbols.py` 是
> 按上游 `check_lib_table.py` 的**检查项名称与判定口径**新写的自包含实现（不复制其源码），
> 因此不存在“修改上游测试用例”的情况。未直接内联该脚本的原因是其依赖链
> `junit.py → common/rulebase.py → common/print_color.py` 属 GPL-3.0 系第三方代码，
> 内联进本仓库（Apache-2.0）会引入许可与维护问题 —— 详见 `notes.md` 第 4 节。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游本仓库无任何测试用例，适配后补全了消费者测试（请在下方说明）
- [ ] **否**，上游已有测试用例覆盖

> 若选择「是」，须说明：
> - **补全的测试范围**：新增 1 个消费者测试程序，共 **26 条断言**，覆盖
>   ① 安装布局（`share/kicad/symbols`、`share/kicad/template/sym-lib-table`、`licenses/LICENSE.md`）；
>   ② 上游 `check_lib_table.py` 的全部 6 类判定 + 库表 uri 占位符可解析性；
>   ③ 222 个库文件的 s-expression 完整性（`(kicad_symbol_lib …)` 头、引号感知的括号配平、
>   非空库、符号总数 22776）；
>   ④ KiCad 读取语义（4 个经典器件存在、具备 `Reference`/`Value` 属性、引脚数正确）。
> - **补全原因**：上游 `kicad-symbols` 仓库自身**不含任何测试程序**（无 `check` 目标、
>   无测试框架、无断言与退出码语义），其校验分散在另一个仓库并由 GitLab 专有 CI 承载；
>   适配后必须让“包内容正确”在 `conan create` 中**每次可回归**，因此按仓库规范
>   （`ci/tools/extract_upstream_tests.sh`：把上游测试源复制进 `test_package/` 并在 `test()`
>   中真实执行）的**精神**补全，并以等价复现方式覆盖上游 `check_lib_table.py` 的判定。
> - **新增测试文件清单**：
>   1. `archives/k/kicad-symbols/10.0.4/test_package/test_kicad_symbols.py` — 消费者测试（26 条断言，仅标准库依赖）
>   2. `archives/k/kicad-symbols/10.0.4/test_package/conanfile.py` — `test()` 中真实执行上述脚本
>   3. `archives/k/kicad-symbols/10.0.4/test_package/MANIFEST.yml` — 上游测试声明（含未纳入项的原因）
>   4. `archives/k/kicad-symbols/10.0.4/reports/test-report.md` — 完整验证报告与负向验证证据

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：**1/1（100%）**（= 上游 `check_lib_table.py` 的全部判定等价复现并真实执行，9 条断言全过；另一项 `comparelibs.py` 因需 git 历史 + `kicad-footprints` 仓库 clone **未纳入**，未计入分母，原因见上文与 `reports/test-report.md`）
- 新增测试用例通过率：**1/1（100%）**（26 条断言全过）

### 构建验证
- 构建系统：CMake（**上游原始 `CMakeLists.txt`，未打任何补丁**）
- 配置选项：**无自定义 `-D`**，全部使用上游默认值（`KICAD_PACK_SYM_LIBRARIES=ON`、`KICAD_DATA=share/kicad`）（R1：参数最少化）
- 编译状态：通过（`conan create` 退出码 0，含 `test_package` 全阶段）
- 编译器：**不调用编译器**（上游 `project( kicad-symbols NONE )`），因此 OHOS aarch64 与本地 x86_64 执行完全相同的构建路径
- 构建期工具依赖：`python3`（上游 `tools/kicad_lib_pack.py`；配方在 `generate()` 用 `shutil.which("python3")` 显式写入 `Python3_EXECUTABLE`，不依赖构建机 PATH 偶然状态）

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 构建无错误 | ✅ | 上游 `pack_symbols` 目标打包 222 个库并通过 CMake `install` 落地 |
| 产物存在性 | ✅ | `share/kicad/symbols/*.kicad_sym` **222** 个、`Simulation_SPICE.sp` 1 个、`share/kicad/template/sym-lib-table`（33741 字节 / 222 条 `(lib …)`）、`licenses/LICENSE.md` |
| 布局正确性 | ✅ | 与 Debian 官方 `kicad-symbols`（10.0.6-1, all）实测布局逐目录一致 |
| 库表一致性 | ✅ | 222 条表项 ↔ 222 个库文件双向无缺、无多、无重复；uri 占位符 `${KICAD10_SYMBOL_DIR}` 可解析到包内真实文件 |
| 数据完整性 | ✅ | 222/222 库文件 s-expression 括号配平、均有 `(kicad_symbol_lib …)` 头、无空库；符号总数 22776 |
| 运行测试 | ✅ | 26/26 断言通过（`conan create` 内真实执行） |
| 动态依赖 | ✅ | 无任何依赖（`requirements()` 为空）；不产出 bin/lib/include |

### R34 负向验证（测试确实依赖被测包）
| 场景 | 结果 |
|------|------|
| 基线（真实包目录） | exit **0**，26/26 PASS |
| 负载完全缺失（空目录作为 package_folder） | exit **1**，`RESULT: FAILED (package layout incomplete)` |
| 只有布局与库表、无任何库文件 | exit **1**，**13/22** PASS（FAIL：packed libraries present / Extra library / Missing library / 符号总数 0 / 已知库不存在） |
| 单个库文件被截断（`power.kicad_sym` 未闭合） | exit **1**，**16/24** PASS（FAIL：括号配平 / 无空库 / `power:GND` 不存在） |

> CI 的 L1e 只搬走 `bin/`、`lib/`、`include/`，本包为资源型包不含这三者，CI 会打印
> `[skip] L1e: No standard artifact dirs found to sabotage`；上表即该验证在本包形态下的
> 等价证据。

### 依赖
- 无第三方依赖（`requirements()` 为空，`build_requirements()` 为空）
- 构建期仅需系统 `python3`（上游打包脚本）

### 遇到的问题与解决方案
1. **平台 `lang=cpp` 与上游纯数据形态不符** —— 逐条取证（`project(... NONE)`、无 C/C++ 源文件、
   Debian `Architecture: all`）后在 PR 中显式说明，按上游真实形态适配（见文首说明）。
2. **`package_type` 不能用 `"application"`** —— CI 门禁 L0k（R38）以
   `package_type == "application"` 作为“本包含 CLI 工具”的判据，会强制要求软件级
   `commands.json`。本包无 bin/，改用 `package_type = "unknown"` + `cpp_info.resdirs = ["share"]`
   （知识库 E255 / E305 同类模式）。
3. **s-expression 括号配平不能直接计数** —— 首版测试用 `text.count("(") == text.count(")")`
   在 5 个库上误报（如 `Connector_Generic.kicad_sym` 两计数相差 60），原因是属性字符串内含括号。
   改为**引号感知**扫描后 222/222 全过。
4. **`(body_styles demorgan)` 使引脚数翻倍** —— 起初按直觉断言 `74xx:74LS00` 有 14 引脚，实测 26
   （4 门 × 3 引脚 × 2 套 body style + 电源单元 2）；断言已按实测值固定（源码 sha256 固定，
   结果确定）。
5. **库表 uri 的占位符解析** —— 打包后 uri 为 `${KICAD10_SYMBOL_DIR}/X.kicad_sym`，校验
   “表项指向真实文件”时必须把占位符解析为包内 `share/kicad/symbols`（KiCad 运行时的取值），
   否则全部误判缺失。
6. **上游测试不可离线复现** —— `comparelibs.py` 需要 git 历史与 `kicad-footprints` 仓库，
   `visual_diff` 需要 KiCad 容器；均如实声明为未纳入，并在 `test_package/MANIFEST.yml`
   与 `reports/test-report.md` 中记录影响面。

### 验证命令
```bash
# OHOS aarch64 构建 + 测试（CI 执行同一条命令）
conan create archives/k/kicad-symbols/10.0.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

# 本地原生等价复现（上游 project(... NONE)，无编译器调用）
conan create archives/k/kicad-symbols/10.0.4 -pr:h=default -pr:b=default

# 单独复跑消费者测试
python3 -B archives/k/kicad-symbols/10.0.4/test_package/test_kicad_symbols.py <package_folder>
```

## 补充说明

- **版本号策略**：`10.0.4` 即上游 tag，首次适配，无修复后缀（R37）。
- **未打任何补丁**：`patches_applied: []`。上游构建逻辑在 OHOS 与原生下均无需改动
  （不调用编译器，只运行 Python 打包脚本）。
- **构建期 Python 版本要求**：上游 `tools/kicad_lib_pack.py` 使用 PEP 604 类型注解
  （`str | None`），需 Python ≥ 3.10；OHOS PC 平台 Python 为 3.12，实测可用（本地验证
  环境为 3.10.12）。若未来 CI worker 降到 3.9 以下，需增加 `from __future__ import
  annotations` 补丁。
- **包体较大**：解压后 221 MB（222 个打包符号库，22776 个符号），压缩传输后约 12 MB 量级；
  这是 KiCad 官方符号库的固有体量（与 Debian 包一致）。
- **未覆盖风险（如实声明）**：上游 `comparelibs.py` 的 KLC 规则检查（引脚命名/引脚类型/图形
  规范等）与 `visual_diff` 渲染对比未在本 PR 中执行；本 PR 保证的是结构完整性、库表一致性、
  关键器件可读性三项。
- **审计**：本地 W3 验证（`conan create` 退出码 0 + 26/26 断言）与 R34 负向验证证据见
  `reports/test-report.md`。
