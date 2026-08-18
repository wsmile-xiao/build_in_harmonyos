# toml 0.10.2 编译笔记

## 基本信息

- **软件名称**: toml
- **版本**: 0.10.2
- **上游仓库**: https://github.com/uiri/toml
- **许可证**: MIT
- **语言**: Python >= 2.6, != 3.0.*, != 3.1.*, != 3.2.*

## 构建信息

### 构建系统

- **类型**: 纯 Python 包
- **构建方式**: pip install --target

### 依赖项

#### 核心依赖

- 无外部依赖

#### 可选依赖

- 无

## 适配说明

### OHOS 平台适配

toml 是一个纯 Python 包，理论上可以在任何支持 Python 的平台上运行。

### 已知限制

1. 无外部依赖，是最简单的纯 Python 包之一
2. 最后更新于 2020年11月1日（已停止维护）

## 验证方法

### test_package

验证 toml 模块的基本可用性：

1. 导入 toml 模块
2. 检查基本功能

## 交付物

- Python 包文件（.py 文件）
- toml 模块

## 参考资料

- GitHub 仓库: https://github.com/uiri/toml
- PyPI 页面: https://pypi.org/project/toml/