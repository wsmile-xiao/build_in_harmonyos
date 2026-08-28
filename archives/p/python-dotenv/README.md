# python-dotenv

## 软件描述
python-dotenv 是一个纯 Python 库，从 `.env` 文件读取键值对并将其设置为环境变量（`dotenv.load_dotenv()`）。

## 功能概述
- **.env 加载**：`dotenv.load_dotenv()` 读取 .env 文件到环境变量
- **CLI 工具**：`python -m dotenv` 命令行操作（set/get/list）
- **解析器**：`dotenv.parser` 解析键值对（支持引号/注释/多行）
- **变量展开**：`dotenv.variables` 环境变量插值

## OHOS 适配

### 构建方式
- **纯 Python noarch**：无编译——`package()` 用 `shutil.copytree` 拷贝 `src/dotenv/` 模块（含 py.typed）到 site-packages
- 绕过 pip/setuptools 构建（setuptools egg_info 加载 entry point 报错实测——同 python-magic/rich）
- `env_info.PYTHONPATH` 暴露导入路径给消费者

### 关键攻坚点
1. **纯 Python 拷贝**：`shutil.copytree` 拷贝源码模块（不依赖 pip 构建）
2. **上游测试实测**：pytest 跑 tests/（sdist 自带 12 个测试文件）——build() 集成回填真实通过率（rule 4，分母=全部用例）
3. **requires-python >= 3.10**：OHOS Python 3.12 满足

### 与 Linux 的差异
- 无差异——纯 Python，全平台行为一致

## 依赖关系
无外部依赖（纯 Python 标准库）。

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.2.3 | built | 2026-08-28 | 纯 Python noarch 适配 |

## 参考资料
- 上游仓库: https://github.com/theskumar/python-dotenv
- PyPI: https://pypi.org/project/python-dotenv/
