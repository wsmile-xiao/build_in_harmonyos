# cssmin

## 软件描述

cssmin 是 YUI CSS Compressor 的 Python 移植版，用于压缩 CSS（去注释、去多余空白/分号、零单位与颜色缩写）。

## 功能概述

- **核心 API**：`cssmin.cssmin(css, wrap=None)`，另有 `remove_comments`、`condense_whitespace`、`normalize_rgb_colors_to_hex` 等可单独调用的压缩阶段函数
- **CLI**：`cssmin:main`（stdin 读原始 CSS，stdout 写压缩结果，支持 `--wrap N`）
- **纯 Python**：仅标准库，无运行时依赖

## OHOS 适配

### 构建方式

- **纯 Python noarch**：无编译——`package()` 用 `shutil.copyfile` 将 `src/cssmin.py` 安装到 `lib/<py_ver>/site-packages`
- `build()` 做 `py_compile` 烟雾检查；上游无测试套件，按 `no_tests` 显式审计接入
- `env_info.PYTHONPATH` 暴露导入路径给消费者

### 与 Linux 的差异

- 无差异——纯 Python，全平台行为一致

## 版本记录

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 0.2.0 | built | 2026-09-12 | 纯 Python noarch 适配，上游无测试套件 |

## 参考资料

- 上游仓库：https://github.com/zacharyvoase/cssmin
- PyPI：https://pypi.org/project/cssmin/0.2.0/
