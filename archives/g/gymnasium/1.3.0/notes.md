# gymnasium 1.3.0 — HarmonyOS PC 适配笔记

## 结论

**路径 A（基础适配）零源码修改。** gymnasium 1.3.0（Farama-Foundation/Gymnasium，
openai/gym 的继任者，MIT）为 100% 纯 Python 包（setuptools，`pyproject.toml`
`[tool.setuptools.packages.find]` 仅打包 `gymnasium` + `gymnasium.*`，无任何
C/Cython/.so 编译产物——已解包 sdist 核实）。OHOS aarch64 原生可用。
上游 sdist 自带的 pytest 套件（`tests/test_core.py` + `tests/testing_env.py`）
在配方 build() 中于 OHOS aarch64 上**真实执行**（未修改任何上游测试文件）。

## 关键决策

### 1. 源码源：官方 PyPI sdist（自带 tests/）

gymnasium 1.3.0 的 PyPI sdist（`gymnasium-1.3.0.tar.gz`，sha256
`6939e86e…`，实测一致）**自带 tests/**（`tests/test_core.py` +
`tests/testing_env.py`）。这与 gym 0.26.2 不同——gym 的 sdist 不含 tests/，
必须回退 GitHub tag tarball。故 gymnasium 直接使用官方 sdist，既稳定又可
真实跑上游测试。

### 2. 上游测试真实执行（L1c）

- 执行方式：`conanfile.py build()` 中 `python3 -m pytest tests/`（sdist 自带，
  `-q --no-header --tb=line`，零 ignore，未改上游断言）。
- `tests/test_core.py` **仅依赖 numpy + pytest**（已 grep 核实，无
  scipy/dill/array_api_extra import）——那些是 `testing` extra 的可选依赖，
  本套件用不到，故不安装，缺省在 test_package/MANIFEST.yml 如实声明，
  而非静默跳过测试。

### 3. 运行时依赖：私有目录安装（非 worker 基线、非 Conan 依赖）

`install_requires`（numpy>=1.21 / cloudpickle>=1.2.0 / typing-extensions>=4.3.0 /
farama-notifications>=0.0.1）与 pytest 由配方 build() 用
`pip install --target <build>/pydeps` 安装到**私有目录**，pin 到已验证版本
（numpy==1.26.4 / cloudpickle==3.1.2 / farama-notifications==0.0.6 /
typing-extensions==4.16.0 / pytest==9.1.1），失败回退不 pin 重试，装后
probe 验证可导入。

**为何不用 conan requires 引用已发布的 numpy/1.26.4**（旧 PR #9265 教训 + 本机实测）：
- 已发布的 numpy/1.26.4 Conan 二进制是 **os.version 6.0** 构建，而本配方
  默认 profile 是 **os.version 5.0**——conan requires 会强制 numpy **源码重编译**
  （meson），在沙箱中易失败，比私有 pip 路径差得多。
- 即便引用成功，conan 发布包的 numpy .so 在 worker 也无法 dlopen（EACCES），
  仍需下方签名/搬迁兜底链。故沿用 gym 的私有 pip 模式最稳。
- 这**不是**"依赖宿主机偶然库"：所有 dep 已在 PINNED 声明并显式安装。

**为何不用 worker 基线**（旧 PR 反复 CI 失败的根因）：worker 的
`/data/service/hnp/bin/python3` 按 user-site 优先加载到另一 uid 属主的
numpy 2.x，其 `_multiarray_umath.cpython-312-aarch64-linux-ohos.so` 被本
进程 dlopen 时报 **Permission denied (EACCES)**。故配方强制
`PYTHONNOUSERSITE=1` 并 `PYTHONPATH=<build>/pydeps` 前置，test() 同样处理。

### 4. numpy 1.26 OHOS 轮子的 libopenblas 桥接

私有目录安装的 numpy 1.26.4 轮子链接 `libopenblas.so.0` 但不自带 numpy.libs。
gymnasium 不依赖 scipy，故 openblas 桥接优先在 pydeps 内搜索任何 `openblas`
.so（含 scipy/.libs 若安装），找不到则回退扫描系统 site-packages。桥接必须在
`import numpy` 探针**之前**执行（镜像 numpy 无 openblas 时 import numpy 报的
"source directory" 误导文案，本质是 dlopen libopenblas.so.0 失败）。

### 5. OHOS dlopen EACCES 兜底链（复刻 gym）

与 gym 完全同款：`_purge_stdlib_shadow`（删 numpy/typing/ 遮蔽子包）、
`_grant_exec`（补 exec 位 + chown 到本进程 uid——worker HMDFS 权限裁剪）、
`_sign_elfs`（binary-sign-tool -selfSign 签名）、`_probe_exec_paths`
（若 build 树无法 dlopen，搬到 $TMPDIR/$HOME/.cache 可加载目录）、
`_diagnose_numpy`（dump 真实底层错误）。

### 6. 鸿蒙特有测试（test_package/test_gymnasium.py）

按 gym 模板设计（真实可运行、不依赖渲染）：
1. 身份：版本 1.3.0 + 从 conan 包导入
2. Env 核心：注册表 + 一个 toy env reset(seed)+step 的 obs 形状/类型/reward
3. spaces 基础：Box contains 边界 + 种子确定性采样
4. 顶层 import numpy + farama_notifications 存在（消费方前置条件）
5. cloudpickle 往返（gymnasium 并行化规范路径）

## 已知限制

- 可选 `testing` extras（scipy/dill/array_api_extra）与可选环境 extras
  （atari/box2d/mujoco/torch/jax/classic-control 渲染）**未适配**——超出核心
  库范围；shipped 测试文件不依赖它们，已如实声明而非虚报。
- 若 worker 无法 dlopen pydeps 内任何 .so 且搬迁也失败，上游 pytest 会如实
  跳过并记录原因（不静默吞掉）。

## TODO

无。
