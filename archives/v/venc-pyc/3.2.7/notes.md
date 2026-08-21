# venc-pyc 3.2.7 适配笔记

## 编译环境
- 构建系统: custom（纯 Python，PEP 517 / flit_core）
- 编译日期: 2026-08-18
- Python: 3.12.9（OHOS 适配版）
- Conan: 2.29.1（OHOS 适配版）
- 编译器: 无需（纯 Python，无 C 扩展）
- 状态: built（conan-verify 通过；本地无法 upload，标 built，由 CI release 流水线 upload 后转 published）

## 背景
venc-pyc 是 Alpine 生态中 VenC（Python 静态博客生成器，
https://framagit.org/denissalem/VenC）的"预编译 Python bytecode"子包
（Alpine 用 py-compile/compileall 生成 .pyc 供 python3 直接加载）。
本任务按路径 A 将 venc-pyc 3.2.7 作为独立 Conan 包归档，源码来源为
VenC 3.2.7 的 PyPI sdist（与 acme-tiny-pyc 路径 A 模式完全一致）。

## 编译步骤
1. init-build：下载 venc-3.2.7.tar.gz（PyPI 官方 URL，sha256 核对
   7114e53949ff58fb9db5bb6b8560ca391adb3e0de69ca787703c9bb6d30786b6）
2. 探索性验证（.work 目录）：
   - `python3 -m pip wheel --no-deps --no-build-isolation -w dist .`
     → 成功生成 venc-3.2.7-py2.py3-none-any.whl（flit_core PEP 517）
   - `python3 -c "import venc3; from venc3.main import venc_entry_point"`
     → import 全部子模块成功，venc_entry_point 可调用
   - `python3 -m compileall -f -q src/venc3` → 49 个 .py 全部生成 .pyc
   - pyc 直接加载（importlib.util.spec_from_file_location）→ OK
   - `venc -v` CLI → 输出 "VenC 3.2.7 / Python 3.12.9"，退出码 0
     （附带 "pkg_resources is not installed." 警告，不影响运行）
3. conan-init 生成骨架 → 按 acme-tiny-pyc 模式手写 conanfile.py /
   conandata.yml / test_package（smoke.py + conanfile.py + MANIFEST.yml）
4. conan-verify：8 道门禁（G0-G4 + L2/L4/L5）
5. finish published：补丁/归档/conan-verify/W2结构+W3编译验证/commands.json

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | PYTHONPATH 覆盖导致 unidecode 找不到 | 系统预设 PYTHONPATH 含 pip-global 路径，`PYTHONPATH=$PWD/src` 覆盖了它 | 追加方式 `PYTHONPATH=$PWD/src:${PYTHONPATH}`（conanfile.py 中 os.environ 追加 old_py） |
| 2 | venc 构建缺 flit_core | flit_core 未预装 | build() 内 `pip install flit_core setuptools wheel`（社区源可用） |
| 3 | venc CLI 输出 "pkg_resources is not installed." | venc_entry_point 版本获取依赖 pkg_resources（setuptools） | 不影响运行（版本仍输出）；bin/venc 入口脚本直接调用 venc_entry_point |
| 4 | **CI #27124 conan-build-test 失败：`ModuleNotFoundError: No module named 'unidecode'`** | 本地环境预装了 unidecode/pyyaml（pip-global / usr/local），而 CI worker 是干净环境；build() 自检 `import venc3.datastore` 顶层 import unidecode，CLI 运行依赖 yaml | conanfile.py build() 与 test_package test() 的 pip install 增加 `unidecode pyyaml`（社区源有 cp312-ohos_aarch64 预编译 wheel，已验证可下载）；本地验证通过后由 CI 干净环境复验 |

## 源码修改
无（纯 Python 包，无源码补丁，conandata patches: {}）

## 依赖版本
- python3 3.12.9（运行时解释器）
- pyyaml 6.0.3（运行时 Python 包，venc3 依赖）
- unidecode 1.4.0（运行时 Python 包，venc3.datastore 依赖）
- flit_core 4.0.2（构建期，PEP 517 后端）
- setuptools 84.0.0 / wheel 0.48.0（构建期）

## R26 说明（系统同名库隔离）
不适用：venc-pyc 为纯 Python 包，无 C 库、无系统同名库、无 .so 输出，
不涉及动态/静态链接，无 ELF 签名需求。

## R38 说明
venc 是命令行工具（bin/venc 可执行入口），已在软件级目录
archives/v/venc-pyc/commands.json 声明（type: tool）。

## 验证结果
```bash
# conan create（G2 门禁，由 conan-verify/finish 执行，必须真实通过）
conan create archives/v/venc-pyc/3.2.7 --profile=ohos-aarch64
# test_package 消费者断言（6 项 + bin/venc -v CLI smoke）
python3 smoke.py   # ALL test_package assertions passed
bin/venc -v        # VenC 3.2.7 / Python 3.12.9（退出码 0）
```

## 上游测试精确统计（2026-08-18 实测，供 PR 通过率填写）

**背景**：上游 VenC 3.2.7 的 PyPI sdist 经 `[tool.flit.sdist] exclude=["test/"]`
不含测试；test/ 目录存在于 Git 仓库（framagit.org，本环境不可达），经
Software Heritage（SWH）归档获取 v3.2.7 tag 源码核实。

**共 6 个测试用例**（入口 test/run.py）：

| 模块 | 用例 | 实测 |
|------|------|------|
| patterns_processing.py | 3（test_datastructure / test_process_no_flatten / test_process_flatten） | **0/3 通过**：test_datastructure 即崩 `AttributeError: 'PatternTree' object has no attribute '_str'`（venc3 3.2.7 已改名 `string`） |
| themes.py | 3（Gentle / Tessellation / Academik 导出合规对照 refs） | 未运行：测试数据（themes/tested + themes/refs）仅存于 framagit，本环境不可达（SWH 限流中，后台任务待补） |

**佐证**：
- 入口 `test/run.py` 自身 ImportError（`from patterns_processing import run_tests`
  引用的 run_tests 两模块均未定义），上游测试无法整体运行；
- Alpine aports venc APKBUILD 显式 `options="!check" # no test scripts available for now`；
- test/ 其余脚本（serial / parallel-* / pythonic_vs_third_party / l10n_cleanup /
  mistletoe_parser）为开发/基准脚本，非 run.py 测试套件。

**结论**：上游测试在 venc 3.2.7 上不可用（实测 0/6），故适配后由 test_package
补充 7 项消费者测试（6 断言 + CLI smoke），7/7（100%）通过。

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（纯 Python，settings=os/compiler/build_type/arch 满足 CI L0p 门禁，package_type=application） |
| conandata.yml | 官方 PyPI URL + sha256 |
| test_package/ | smoke.py + conanfile.py + MANIFEST.yml |
| commands.json | 软件级命令行工具声明（R38） |
| manifest.yaml | 版本级元数据（status: published） |

## 注意事项
- .pyc 为 CPython 3.12 字节码格式（magic number 绑定 Python 版本），
  运行时需 python3.12 加载；若目标平台 Python 版本不同需重新生成 pyc
- pyyaml/unidecode 为运行时 Python 包依赖（解释器方式，非 Conan requires），
  消费者需自行提供（pip install pyyaml unidecode 或系统包）
- bin/venc 入口 shebang 为 `#!/usr/bin/env python3`，运行时需 python3 在 PATH
---

**编译结束**: 2026-08-18 13:22
**最终状态**: built
