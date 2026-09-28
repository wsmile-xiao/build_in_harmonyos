# DRAFT-E733 — 上游测试数据生成依赖 numpy：沙箱 HOME pip --user 装 ohos wheel

- **任务**: libnpy 1.0.1（2026-09-25）
- **号段**: DRAFT-E733（`knowledge_id.py --claim` 三面扫描取号）
- **状态**: DRAFT — 待维护方审入 graph

## 现象

libnpy 的 `tests/createnpy.py` 用 `numpy.save` 生成全部 `.npy` 夹具（meson
`custom_target gen-data` 在构建测试时调用），设备 python3 没有 numpy：

```
ModuleNotFoundError: No module named 'numpy'
```

上游 CI 靠 `pip install numpy` 解决，但本工作区禁止改全局 pip/系统 Python（AGENTS §2），
且上游 CI 的 `pip install numpy` 在设备真实 HOME 下执行同样违反沙箱 HOME 口径。

## 根因与修法

- 根因：上游把 numpy 当**测试生成期依赖**（不是库本身依赖），设备 python 环境不带；
- 修法：**沙箱 HOME 下任务私有安装**——

```bash
TD="$HOME/tmp/libnpy-1.0.1"
mkdir -p "$TD/test-home"
HOME="$TD/test-home" python3 -m pip install --user meson numpy
HOME="$TD/test-home" python3 -c "import numpy; print(numpy.__version__)"   # 2.5.3
```

- PyPI 实测直接给出原生 wheel：`numpy-2.5.3-cp312-cp312-ohos_aarch64.whl`
  （本机 `sysconfig.get_platform()` = `ohos-aarch64`），秒级装完、无需编译；
- 运行测试保持同一 `HOME`（user-site 路径随 HOME 解析），`meson` 也同批装在
  `$TD/test-home/.local/bin`（设备 PATH 原本无 meson）；
- **不进 conan 配方**：配方零运行依赖，CI 不需要 numpy（上游测试不进 build()）。
  若某包必须在 build() 里用 numpy，改走 ohpcd `numpy/1.26.4`（OHOS 预编译包）注入
  PYTHONPATH——注意包内 `lib/pythonX.Y/site-packages` 目录按**打包时** python 版本命名。

## 复现命令（设备可直接执行）

```bash
TD="$HOME/tmp/libnpy-1.0.1"
HOME="$TD/test-home" python3 -c "import numpy,sys; print(numpy.__version__, sys.platform)"
# 期望：2.5.3 ohos
# 反向复现（未装环境）：python3 -c "import numpy" → ModuleNotFoundError
```

日志证据：`$HOME/tmp/libnpy-1.0.1/pip-install.log`（2026-09-25 沙箱安装轮）。
