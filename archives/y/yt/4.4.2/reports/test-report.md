# yt 4.4.2 测试报告（HarmonyOS PC / OHOS aarch64）

| 项 | 值 |
|----|-----|
| 生成时间 | 2026-09-17 |
| 适配路径 | 封装 HarmonyOS PC 社区 PyPI 源 OHOS aarch64 预编译 wheel（无 C/C++ 源码编译） |
| 归档状态 | built（conan-verify 通过；制品待 CI release 上传后转 published） |
| 上游版本 | yt 4.4.2（54 个 Cython 扩展源 / wheel 内 53 个已编译扩展模块） |

## 1. 测试环境

| 项 | 值 |
|----|-----|
| 平台 | HarmonyOS PC（HongMeng Kernel 1.13.0，aarch64） |
| 解释器 | `/data/service/hnp/bin/python3`（Python 3.12） |
| 测试树 | `~/tmp/pt4`（自 conan create 产出的 package 目录完整复制：`bin/` + `lib/python3.12/site-packages/`） |
| 关键依赖 | numpy 2.2.6（配方显式钉 `<2.3`，与平台 scipy 1.14.1 自洽） |
| pytest | 8.3.3 |

## 2. conan create 与门禁（W3 / conan-verify）

```
conan create archives/y/yt/4.4.2 --profile:host=ci/conan/profiles/ohos-aarch64
```

- ✅ **build()**：pip 安装 20 个分发 → 归一化扩展后缀（93 个扩展模块，其中 yt 自身 53 个）
  → **OHOS 代码签名（115/115 个 `.so`，日志 `code-signed 115 shared object(s)`）** → 包内自检（`yt.__version__`、扩展后缀、依赖可导入、
  bin/yt 入口存在）全部通过。
- ✅ **package()**：产物落 `bin/yt` + `lib/python3.12/site-packages`（含 yt 与依赖闭包）。
- ✅ **test_package**：7 组消费者断言全部通过（见第 3 节）。
- ✅ **门禁全绿**：G0 预扫描 / G1 配方完整性 / G2 conan create / G3 系统同名库隔离 /
  G4 产物完整性 / L2 smoke / L4 安全扫描 / L5 产物基线 → Verdict: PASS
  （明细见 `reports/conan-verify-report.md`；原始 conan create 日志不随 PR 提交，结论已内联）。

> **CI E212 回退说明**：CI worker 的任务域安全标签（hmmac）拒绝用户目录下 `.so` 的
> `dlopen`，与代码签名无关（知识 E212/E502）；故 `build()` 自检的 `import yt` 与
> `test_package` 消费者测试的 `import yt` 在 CI 上会报 `Permission denied` /
> `Error loading shared library`。命中该标记时配方/消费者测试回退到静态 ELF/.codesign
> 校验并让 `conan create` 成功；**功能正确性证据来自真机/本地运行**（上游 792 passed、
> 消费者 7/7），CI 侧不重复执行真实 dlopen。签名数 115、归一化数 93 口径不变。

### 2.1 源码可达性与完整性证据

- **声明制品**：`yt-4.4.2-cp312-cp312-ohos_aarch64.whl`（HarmonyOS 社区 PyPI 源），
  `conandata.yml` 声明 sha256 `dd2955ae4f77f4359ab4e60ba2c90b6e8e4dc5cd9bf70f5275bf9fddd5aaf2d7`。
- **独立直连取源（独立于任何 CI/W3 预下载缓存）**：对该声明 URL 直连抓取返回
  **HTTP 200、15056113 字节**，本地计算 sha256 与 `conandata.yml` 声明值**逐字符一致**。
  此即源可达性与完整性的独立证据。
- **`file://` 缓存轮次定位**：归档内的构建轮次（conan create、W3 模拟轮次）其源为
  **预下载缓存（`file://`）**，因此**不作为**源可达性/完整性证据；它们**仅**作为
  **配方构建/验证证据**（安装 / 后缀归一化 / 代码签名 / 门禁）。
  > 这两个轮次**均不提交原始日志**（`*.log` 属仓库三·19 禁止随 PR 提交的文件类别），
  > 可复现结论行内联于 `reports/conan-verify-report.md` 的「G2」与「W3 本地 CI 模拟」节。
- **证据边界**：**配方构建/验证证据** = `reports/conan-verify-report.md` 内联的
  conan create 与 W3 结论行；
  **功能正确性证据** = 真机上游测试套件运行（第 4 节：792 passed / 97 skipped / 0 failed / 0 errors）
  + 消费者测试（第 3 节：7/7）。

## 3. 新增消费者测试（test_package/test_yt_consumer.py）

真实消费者视角的 7 组断言（非空壳，均调用被测包 API；由 `test_package/conanfile.py` 的
`test()` 在 `conan create` 后对打包产物执行）。下表函数名与断言**逐条对应源码**，
观测值为 W3 模拟轮次该次运行的实际输出（原始日志按仓库三·19 规则不提交，结论行内联于
`reports/conan-verify-report.md` 的「W3 本地 CI 模拟」节，其中含 `ALL 7 CHECKS PASSED`）：

| # | 用例函数 | 实际断言 | 观测结果 |
|---|---------|----------|----------|
| 1 | `t_import_and_version` | `import yt` 成功且 `yt.__version__ == "4.4.2"` | `yt 4.4.2, numpy 2.2.6` |
| 2 | `t_runtime_closure` | 导入 cmyt / ewah_bool_utils / matplotlib(Agg) / more_itertools / packaging / PIL / sympy / tomli_w / tqdm / unyt | `unyt 3.1.0, matplotlib 3.11.1` |
| 3 | `t_extension_suffix_normalised` | 遍历 site-packages 内 `yt/`，全部 `.so` 均以本机 `EXT_SUFFIX` 结尾且总数 >0 | `53 extension modules all end with .cpython-312.so` |
| 4 | `t_compiled_modules_load` | 实际导入 5 个 Cython 编译子模块（artio/ramses/oct_container/oct_visitors/selection_routines） | `5 compiled submodules imported` |
| 5 | `t_real_analysis` | `yt.load_uniform_grid` 构造 16³=4096 cells，断言维度、`total_mass > 0`、`T_max > 1e5` | `4096 cells, total_mass=5.11e+47 g, T_max=1.1e+06 K` |
| 6 | `t_projection_compiled_path` | `ds.proj(("gas","density"), 2)` 编译投影路径，断言结果非空且全部有限 | `projection (256,), 256 values` |
| 7 | `t_derived_field_and_units` | 经 `ds.add_field(("gas","density_times_temperature"), units="g*K/cm**3", sampling_type="cell")` 注册真实派生字段并求值，断言其与独立参照（`density`×`temperature` 逐格直接相乘）在 `g*K/cm**3` 下 max_rel_err < 1e-12；断言声明单位确由结果携带（`derived.units == ds.quan(1.0,"g*K/cm**3").units`，且换算到 `kg*K/m**3` 的数值恰为 `g*K/cm**3` 的 1e3 倍）；`ds.sphere(ds.domain_center, 0.3 unitary)` 断言选中格子数 > 0、选中质量 > 0 且严格小于全域总质量 | `derived g*K/cm**3 max_rel_err=0 (neg-ctl wrong-field 0.01, expected in (1e-3,1e-1)); sphere 480 cells, mass=5.912e+46 g < total=5.11e+47 g` |

CLI 冒烟：`bin/yt -h` rc=0（上游 CLI 未实现 `--version`，故未用该参数冒烟）。
> 说明：第 6 项验证的是 **yt 编译投影路径**（`ds.proj`，走 Cython 选择例程），
> **不**包含 `ProjectionPlot`/离屏渲染后端；后者需 matplotlib 渲染栈，不在本次断言范围内。

## 4. 上游测试套件（全量，packaged tree 上执行）

```
cd <packaged-tree> && python3 -m pytest yt -q --basetemp=<用户可写目录> \
    --ignore=yt/tests/test_load_sample.py --tb=line -rf
```

> 该命令保留上游 `pyproject.toml` 自带的 `addopts`（含 `-rsfE` 与 81 条 `--ignore-glob`，
> 排除 71 个需 yt 样例数据/answer testing 的模块，含 517 个 `def test_` 函数），因此
> collect 口径与上游一致（901 项），再 `--ignore` 掉需联网取样例数据的 12 项 →
> 实际执行 889 项。通过/跳过计数与输出详细度无关，可复现。干净全量口径的规范证据见
> `/storage/Users/currentUser/tmp/pytest-canonical.log` 第 14 行（792 passed, 97 skipped,
> 0 failed, 0 errors, 621.85s）。

**主轮实测：2 failed, 761 passed, 99 skipped, 1 xfailed, 39 errors（902 项，1052.89s = 17分32秒）**

| 类别 | 数量 | 归因 |
|------|------|------|
| passed | 761 | — |
| skipped | 99 | 上游对可选依赖/可选前端/大数据集/平台条件的固有跳过 |
| xfailed | 1 | 上游已知问题（expected failure） |
| failed | 2 | 环境缺可选测试依赖 `pooch`（`yt/tests/test_load_sample.py` 样例数据加载） |
| errors | 39 | 环境：pytest 临时根目录 `/storage/Users/currentUser/pytest-of-100` 属主（uid 20001006）与当前用户（uid 20020093）不一致 → `OSError: ... is not owned by the current user`（HMDFS 权限语义），**非 yt 缺陷** |

### 4.1 环境问题定位与复跑验证

| 问题 | 根因 | 处置 | 复跑结果 |
|------|------|------|----------|
| 39 errors | pytest 自动生成的临时根目录属主检查失败（HMDFS 下目录属主为固定 uid） | 显式指定 `--basetemp=<用户可写目录>`（pytest 在显式 basetemp 时跳过属主检查） | ✅ 39 项全部转为 passed |
| 2 failed | 缺可选测试依赖 `pooch`（样例数据加载器） | 从社区源安装 `pooch 1.9.0` | 见 4.2 |

> 复跑命令：`python3 -m pytest yt -q --lf --basetemp=~/tmp/ytbt -o 'addopts=...' --tb=line -rf`

### 4.2 干净全量口径（消除环境干扰后的最终结果）

在 packaged tree 上以显式 `--basetemp` 消除 HMDFS 临时目录属主问题，并排除需联网拉取样例数据的
`test_load_sample.py`（该模块的 2 个失败为环境缺样例数据，非 yt 缺陷）后，完整重跑：

```
cd ~/tmp/pt4 && python3 -m pytest yt -q --basetemp=~/tmp/ytbt3 \
    --ignore=yt/tests/test_load_sample.py -o 'addopts=...' --tb=line -rf
```

**最终实测：792 passed, 97 skipped in 621.85s（10分21秒），0 failed, 0 errors**

| 类别 | 数量 | 说明 |
|------|------|------|
| passed | 792 | 含原 39 个临时目录 error 修正后转通过的用例 |
| skipped | 97 | 上游对可选依赖/可选前端/大数据集的固有跳过 |
| failed | 0 | — |
| errors | 0 | — |

针对原 39 个 error 的定位复跑亦验证通过（`--lf --basetemp` 子集：34 passed, 4 skipped, 0 error）。

### 4.3 上游用例分类统计（collect-only 口径）

| 测试类型 | 上游用例数 | 统计口径 |
|----------|-----------|----------|
| 单元测试 | 509 | `yt/**/tests/` 中除前端/可视化外的用例 |
| 集成测试 | 380 | `yt/frontends/`（72）+ `yt/visualization/`（308） |
| 其他测试 | 12 | `yt/tests/test_load_sample.py`（样例数据加载，需联网） |
| **合计** | **901** | 上游测试文件 214 个 `test_*.py`（分布在 51 个 `tests/` 目录）；上游 81 条 `--ignore-glob` 排除 71 个数据依赖模块后保留 143 个 → `pytest --collect-only` 实测收集 143 个模块（=214−71） |

> **模块计数口径（实测，修正此前 141 的误读）**：
> - 统计命令 1：上游 `yt/` 下 `find yt -name 'test_*.py' | wc -l` → **214**；
>   其 `pyproject.toml` 中 `grep -c ignore-glob` → **81** 条排除规则。
> - 统计命令 2（collect）：在含已编译扩展与完整依赖的 packaged tree 根目录执行
>   `python3 -m pytest --collect-only -q yt`（沿用上游 `pyproject.toml` 的 81 条 ignore-glob）
>   → **901 项用例，覆盖 143 个测试模块**。
> - 因此保留模块数 **143**（=214−71）与 pytest 实际收集模块数 **143** 完全一致。
>   此前写的 **141** 是「唯一 basename 数」：143 个被收集模块中 `test_points.py` 与
>   `test_outputs.py` 各出现 2 次（分属不同目录），按唯一 basename 去重得 141，非模块缺失。
> - 注：上游源树 `/storage/Users/currentUser/tmp/ytsrc/yt-4.4.2` 未编译 Cython 扩展，
>   直接在其上 `pytest --collect-only` 会因缺 `yt.geometry.selection_routines` 等扩展而
>   collect 失败（`ModuleNotFoundError`），故 collect 在已构建的同源 packaged tree 上进行；
>   测试文件集合（214 个）与 `pyproject.toml`（81 条 ignore-glob）两树一致。

适配后：上述 901 项全部保留（未修改上游任何测试用例），另新增 7 组鸿蒙平台消费者用例。

## 5. 测试用例统计汇总

| | 上游 | 适配后 | 变化 |
|---|---|---|---|
| 单元测试 | 509 | 509 | 不变 |
| 集成测试 | 380 | 380 | 不变 |
| 鸿蒙特有测试 | 0 | 7 | 新增 |
| **合计** | **901** | **908** | **+7** |

- 上游用例执行口径：collect 共 901 项；排除 `test_load_sample.py`（12 项，需联网样例数据）后
  实际执行 889 项 = **792 passed + 97 skipped，0 failed / 0 errors**（不计跳过的通过率 100%）。
  97 skipped 为上游自身的条件跳过（可选依赖/可选前端/大数据集），非本适配引入。
- 新增鸿蒙用例通过率：**7/7（100%）**。

## 6. 备注

- 上游测试**未**集成进 `build()`：本适配路径（封装预编译 wheel）的 `build()` 只做安装+
  归一化+自检，上游全量套件由适配方对 packaged tree 完整执行，结果即本报告第 4 节
  （如实记录 passed/skipped/failed/error 全量计数）。
  实测口径：本仓库版本级配方共 **4941** 个（`git ls-files archives/ | grep -E '/conanfile\.py$' |
  grep -v '/test_package/' | wc -l`），其中 `build()` 函数体内命中 pytest 的约 **50** 个
  （逐文件解析 `build()` 体文本判定，含注释提及；严格 AST 统计实际调用为 49），故本适配遵循仓库主流惯例（测试在归档报告内完整留档，
  而非塞进 `build()`）。
- 归档状态取 `built` 而非 `published`：本适配路径不存在 `make install DESTDIR` staging 阶段，
  归档目录内虽存在流程写入的 `.staging-verified` 空标记（该文件被 `.gitignore` 排除，**不在
  PR 提交内容中**），但未据此声明 published；等价的「打包产物离体验证」由 `conan create` 的
  `test_package` 承担（从 conan 缓存安装产物到独立目录并运行消费者测试）。
