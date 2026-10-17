# gym 0.26.2 — HarmonyOS PC 适配笔记

## 结论

**路径 A（基础适配）零源码修改。** gym 0.26.2（openai/gym 最后一个官方版本，MIT）
为 100% 纯 Python 包（无 C 扩展、无 POSIX-only API），OHOS aarch64 原生可用。
上游 pytest 全量套件（1336 用例）在配方 build() 中于 OHOS aarch64 worker 上
**真实执行**（未修改任何上游测试文件）。

## 关键决策

### 1. 源码源：GitHub tag tarball 而非 PyPI sdist

PyPI sdist（`gym-0.26.2.tar.gz`，sha256 `e0d882f4…`）经 `tar tzf` 核实**不含
tests/ 目录**——用它无法真实运行上游测试（会沦为虚报）。故采用 GitHub tag
tarball（含完整 tests/，sha256 `96a5fc83…`，两次下载一致）。

### 2. 上游测试真实执行（L1c）

- 执行方式：`conanfile.py build()` 中 `python3 -m pytest tests/ -q --tb=no`
- 排除 4 个收集期错误文件（**非上游 install_requires 的可选 extras**）：
  | 文件 | 原因 |
  |------|------|
  | tests/envs/test_env_implementation.py | 需 box2d+pygame（gym[box2d] extra） |
  | tests/utils/test_play.py | import pygame（extra） |
  | tests/utils/test_save_video.py | 需 moviepy（extra） |
  | tests/wrappers/test_atari_preprocessing.py | 需 ale（atari ROMs extra） |
- 基线（OHOS aarch64 / numpy 1.26.4 / pytest 9.1.1 / Python 3.12.9，~45 s）：
  **1336 收集；1242 passed / 81 failed / 13 skipped**
- 81 失败逐条归因（**0 个 OHOS 适配回归**，属环境/版本漂移）：
  | 数量 | 原因 |
  |------|------|
  | 38 | numpy>=1.24 `np.bool8` 弃用告警触发上游告警断言（上游按 numpy<1.24 写的套件） |
  | 28 | 需可选 extra box2d/pygame（render 模式、box2d 环境） |
  | 7 | 需可选 extra moviepy（录像） |
  | 4 | MultiDiscrete/MultiBinary sample_contains 边界在新 numpy 语义下变化 |
  | 3 | pytest 版本告警断言漂移 |
  | 1 | Python 3.12 移除 `pytest.warns(None)` 用法 |
- 按 TEST_QUALITY_SPEC 3.3 声明豁免（test_package/MANIFEST.yml），
  不删除 pytest 调用、不改上游断言、不虚报。

### 3. 运行时依赖：私有目录安装（非 worker 基线、非 Conan 依赖）

install_requires（numpy>=1.18 / cloudpickle>=1.2.0 / gym_notices>=0.0.4）与
pytest 由配方 build() 用 `pip install --target <build>/pydeps` 安装到**私有
目录**，pin 到已验证版本（numpy==1.26.4 / scipy==1.17.1 / cloudpickle==3.1.2 /
gym_notices==0.1.0 / pytest==9.1.1），失败时回退不 pin 重试，装后 probe
验证可导入。scipy 仅作 `libopenblas.so` 提供方（gym 不 import 它），
pin 1.17.1 而非 1.18.0——1.18.0 要求 numpy>=2.0，与 numpy 1.26.4 冲突。

**为何不用 worker 基线（首轮 CI #36858 失败教训）**：worker 的
`/data/service/hnp/bin/python3` 按 user-site 优先加载到
`$HOME/.local/lib/python3.12/site-packages/numpy`（numpy **2.5.2**，属主
为另一 uid），worker 进程 uid=100 dlopen 其
`_multiarray_umath.cpython-312-aarch64-linux-ohos.so` 时 **Permission
denied (EACCES)**——本地开发机以属主 uid 运行故未暴露。故配方强制
`PYTHONNOUSERSITE=1` 并 `PYTHONPATH=<build>/pydeps` 前置，test() 同样处理。
私有目录归构建进程所有、必然可读，同时隔离 gym 对 numpy 1.x 的要求与
user-site 的 numpy 2.x（上游明确不支持 2.x）。

### 4. numpy 1.26 OHOS 轮子的 libopenblas 桥接

私有目录安装的 numpy 1.26.4 轮子链接 `libopenblas.so.0` 但不自带 numpy.libs；
scipy 1.17.1 轮子带 `scipy/.libs/libopenblas.so`（无 `.0` 后缀）。配方
`_bridge_openblas()` 优先从私有 pydeps 内的 scipy 取该文件，链接到
`pydeps/numpy.libs/libopenblas.so.0`——numpy 扩展的 RPATH
（`$ORIGIN/../../numpy.libs`）直接命中，**不依赖 LD_LIBRARY_PATH**
（兜底仍会注入 LD_LIBRARY_PATH，并回退扫描系统 site-packages）。
桥接必须在 `import numpy` 探针**之前**执行：镜像 numpy 无 openblas 时
`import numpy` 报的 "source directory" 误导文案，本质是 dlopen
libopenblas.so.0 失败。

### 5. 鸿蒙特有测试（6 项，test_package/test_gym.py）

1. 身份：版本 0.26.2 + 从 conan 包导入
2. CartPole 核心：reset(seed)+50 步 step，obs 形状/类型/reward 语义
3. SyncVectorEnv×2：批量 reset/step 形状
4. cloudpickle 往返（gym 并行化规范路径）：类型保留 + 反序列化后可用
5. spaces 种子确定性采样 + Box contains 边界
6. TimeLimit 包装器：max_episode_steps=5 精确截断

## 已知限制

- 上游自 2022 停止维护（import 时打印迁移 gymnasium 横幅）；本适配仅保证
  OHOS aarch64 上可用，不承诺 numpy 2.x 兼容（上游明确不支持）。
- 可选 extras（box2d/pygame、moviepy、ale、atari ROMs）未适配——超出
  核心库范围；上游测试中相关 81 失败已如实归因。

## TODO

无。
