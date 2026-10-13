# rl-accel 0.9.1 适配笔记

## 软件识别

- 名称：rl-accel（ReportLab accelerator）
- 版本：0.9.1
- 上游：http://www.reportlab.com/ （PyPI Owner = reportlab；官方唯一分发渠道为 PyPI）
- 构建系统：setuptools（pyproject.toml → setuptools.build_meta）
- 产物形态：**单个 CPython C 扩展模块** `_rl_accel`，源文件 `src/_rl_accel.c`；
  `setup.py` 中 `packages=[]`，PyPI wheel 内只有 `_rl_accel.abi3.so`（cp37-abi3）。

## 语言判定核验（R47）

`lang-preflight` 的输出与任务语言不符，按 R47 附录 D.4 边界规则逐项核验：

```
$ python3 scripts/ohc-run.py lang-preflight rl-accel 0.9.1 --src <src>
{"expected": "cpp", "detected_language": "python",
 "language_evidence": {"build_system": "setuptools",
                       "manifest": "pyproject.toml 存在（python 打包 manifest）",
                       "source_stats": "源文件 4 个（python:3, c:1），主体占比 75%"}}
```

| 核验项 | 证据 | 归属 |
|---|---|---|
| 唯一编译产物 | `src/_rl_accel.c`（1342 行 C，模块 11 个函数 + 类型全在此） | **主体（C）** |
| setup.py | 构建脚本（Extension 声明 / abi3 产物名） | 辅助脚本（D.4 不计入主体） |
| tests/testcs.py、tests/testrc.py | 上游测试脚本 | 辅助脚本（D.4 不计入主体） |
| pyproject.toml | 只有 build-system 段（打包元数据） | 辅助清单 |

结论：按主库主体判 **c/cpp（c↔cpp 兼容族）**，继续 conan 适配主流程。
同口径先例：`knowledge/DRAFT-cmsis-dsp-1.18.0-lang-preflight-pyproject-python-misdetect`、
`knowledge/DRAFT-exr_image-0.1.0-rc3-lang-preflight-aux-manifest`
（rec_approach = main-body-first-then-compat-family）。

## 编译环境

- 目标：aarch64-linux-ohos（OHOS 6.0 / clang 15 / musl）
- 依赖：python/3.12.9（Python.h + libpython3.12.so）
- 构建日期：2026-10-12

## 编译步骤（等价上游 `setup.py build_ext`）

```bash
# <py> = python/3.12.9 制品包目录
clang -shared -fPIC -O2 \
      -DPy_LIMITED_API=0x03070000 \
      -I"<py>/include/python3.12" src/_rl_accel.c \
      -o _rl_accel.abi3.so \
      -L"<py>/lib" -lpython3.12
```

- `-DPy_LIMITED_API=0x03070000` 与产物名 `_rl_accel.abi3.so` 对齐上游 abi3 wheel
  （Wheel Tag: `cp37-abi3`）。
- 上游 setup.py 只在能导入 `bdist_wheel.get_abi_tag` 时才启用有限 API；本配方
  直接固定该宏 = 复现对应发布配置，避免依赖 setuptools/wheel。
- 产物安装到 `<prefix>/lib/python3.12/site-packages/_rl_accel.abi3.so`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 判 detected=python，与任务 cpp 不符 | 工具按文件名计数（setup.py/tests/*.py 多于 .c）且全树 manifest 扫描，未应用 D.4「辅助脚本不算主体」 | 按 D.4 核验主库主体（唯一编译产物为 C）后判 c/cpp 继续；证据与方法记入 manifest/notes（见上节） |
| 2 | musl 下 import 扩展需显式链接 libpython | musl 不把 Python 符号导出到全局符号表（glibc 下 abi3 模块无需 NEEDED libpython） | 链接时加 `-lpython3.12`；产物 NEEDED 含 `libpython3.12.so.1.0`（鸿蒙专项测试断言该项） |
| 3 | `_PyArg_ParseTuple_SizeT`（有限 API 私有符号）解析 | 上游有限 API 构建刻意使用该私有符号 | 实测 python/3.12.9 的 libpython3.12.so 导出该符号（`llvm-nm -D` 可见），显式链接即可解析；无需改源码 |
| 4 | setuptools 未发布到 ohpcd | ohpcd 无 setuptools 制品 | 不写 tool_requires（PF4），直接调 clang 复现 build_ext |

## 源码修改

**无**。未改动上游任何源码，无补丁（patches/ 为空）。

## 依赖版本

| 依赖 | 版本 | 用途 |
|---|---|---|
| python | 3.12.9 | Python.h（头文件）与 libpython3.12.so（链接期必需） |

## 上游测试（R51）

上游 sdist 的 `tests/` 只有 2 个可执行测试入口，**无 pytest/unittest 注册**：

```bash
# build() 内用 python/3.12.9 解释器真实执行（PYTHONPATH=构建目录）
python3 tests/testcs.py    # → calcChecksum(b"Hello cruel world!")=142323306
python3 tests/testrc.py    # → [4, 2, 4294967295, 4, 2] / 同值（无 '!!!!!' 告警）
```

- 用例总数 2，通过 2，失败 0，跳过 0。
- 日志：`build-release/upstream-tests.log`（conan create 构建目录内）。

## 验证结果

```bash
$ conan create archives/r/rl-accel/0.9.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# build() 内上游测试：2/2 PASS
# test_package 消费者 API：64/64 passed
# test_package 鸿蒙专项：13/13 passed
```

## 交付物

| 文件 | 说明 |
|---|---|
| `lib/python3.12/site-packages/_rl_accel.abi3.so` | 加速扩展（含 .codesign 段） |
| `licenses/LICENSE.txt` | 上游许可证（BSD-3-Clause） |

## 新增鸿蒙专项测试（test_package/test_rl_accel_ohos.py，13 项断言）

只依赖标准库，直接校验**已打包产物**在 OHOS 上的平台事实：

1. ELF 身份：64 位、小端、`e_machine = EM_AARCH64(183)`；
2. 带 `.codesign` 段（OHOS 沙箱 dlopen 强校验；缺失时报误导性 `Permission denied`，E212）；
3. `NEEDED` 含 `libpython3.12.so.1.0`（musl 适配点）与 `libc.so`；
4. 产物名 `_rl_accel.abi3.so`；
5. 运行期在 musl 下复算 `fp_str`（libc snprintf 数值格式化）、`calcChecksum`
   （大端 32 位字累加）、`asciiBase85`（位运算）确认无平台偏差。

## 注意事项

- 扩展是 abi3（有限 API）产物，文件名 `_rl_accel.abi3.so` 由 CPython 的
  `EXTENSION_SUFFIXES` 识别（`['.cpython-312-aarch64-linux-ohos.so', '.abi3.so', '.so']`），
  `import _rl_accel` 可直接命中。
- 消费者需能从 `lib/python3.12/site-packages` 导入：包侧 `package_info()` 用
  `runenv_info`/`buildenv_info` 声明 PYTHONPATH。
---

**编译结束**: 2026-10-12 13:01
**最终状态**: built
