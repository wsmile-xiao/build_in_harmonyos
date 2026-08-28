# tomli

## 软件描述
tomli 是一个纯 Python 的 TOML 解析器（Python 3.8+），提供 TOML 1.0 规范的完整解析能力（`tomli.load()` / `tomli.loads()`）。

## 功能概述
- **TOML 解析**：`tomli.load()` / `tomli.loads()` 解析 TOML 到 dict
- **TOML 1.0 规范**：支持 TOML v1.0 全部特性（表/数组/内联表/多行字符串等）
- **标准库 tomllib 的后端**：Python 3.11+ 的 `tomllib` 即基于 tomli
- **类型转换**：自动转换为 Python 原生类型（datetime/bytes/float 等）

## OHOS 适配

### 构建方式
- **纯 Python noarch**：无编译——`package()` 用 `shutil.copytree` 拷贝 `src/tomli/` 模块（含 py.typed）到 site-packages
- 绕过 pip/setuptools 构建（setuptools egg_info 加载 entry point 报错实测——同 python-magic/rich）
- `env_info.PYTHONPATH` 暴露导入路径给消费者

### 关键攻坚点
1. **纯 Python 拷贝**：`shutil.copytree` 拷贝源码模块（不依赖 pip 构建）
2. **上游测试实测**：sdist 不含 tests/（仅 GitHub 仓库有）——build() 从 GitHub 2.4.1 tag 下载 tests/（含 toml-test 数据）跑 pytest，回填真实通过率（rule 4，分母=全部用例）
3. **TMPDIR 指向可写目录**：沙箱 /tmp 只读 + pytest-of-<uid> 属主检查（同 python-dotenv 教训）

### 与 Linux 的差异
- 无差异——纯 Python，全平台行为一致

## 依赖关系
无外部依赖（纯 Python 标准库）。

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 2.4.1 | built | 2026-08-28 | 纯 Python noarch 适配 |

## 参考资料
- 上游仓库: https://github.com/hukkin/tomli
- PyPI: https://pypi.org/project/tomli/
