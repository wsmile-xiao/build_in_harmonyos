# yt

yt（<https://yt-project.org>）是用于分析天体物理模拟数据的 Python 工具包，提供
网格/粒子数据前端（Enzo、Gadget、ARTIO、RAMSES、HDF5 等）、投影/切片可视化、
派生场与单位系统。

| 项目 | 值 |
|------|-----|
| 上游版本 | 4.4.2 |
| 上游仓库 | <https://github.com/yt-project/yt> |
| 许可证 | BSD-3-Clause |
| 适配平台 | HarmonyOS PC (OHOS aarch64) |
| 适配路径 | 封装社区源 OHOS 预编译 wheel（无 C/C++ 源码编译） |

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| [4.4.2](4.4.2/) | built | 封装 `yt-4.4.2-cp312-cp312-ohos_aarch64.whl`，扩展后缀归一化 + 依赖闭包自包含 |

## 安装

```bash
conan install --requires=yt/4.4.2 -r=ohpcd
```

包内已捆绑 yt 与其运行时依赖（numpy、matplotlib、unyt、cmyt、ewah_bool_utils、
more-itertools、tqdm、sympy、pillow 等 20 个分发），安装后离线即可使用：`PYTHONPATH` 与
`bin/yt` 由 `package_info()` 的 `runenv_info` 提供。

## 使用

```bash
# CLI
yt --help
yt stats <dataset>

# Python API（依赖 conan 注入的 PYTHONPATH）
python3 -c "import yt; print(yt.__version__)"
```

## 适配说明

- **扩展后缀归一化**：wheel 的扩展名为 `*.cpython-312-aarch64-linux-ohos.so`，本机
  Python 只识别 `EXT_SUFFIX`（`.cpython-312.so`），安装后统一重命名。
- **numpy 上限**：平台 scipy 1.14.1 要求 `numpy<2.3`，配方显式钉版本以保证依赖闭包自洽。
- **自包含 CLI**：`bin/yt` 为按相对路径定位包内 `site-packages` 的启动器，不依赖构建机路径。

详见 [4.4.2/notes.md](4.4.2/notes.md)（含上游测试与消费者测试实测数据）。
