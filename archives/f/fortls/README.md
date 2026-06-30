# fortls

## 简介

fortls 是 Fortran 语言服务器协议 (LSP) 的 Python 实现，为支持 LSP 的代码编辑器（如 VS Code、Vim、Emacs 等）提供 Fortran 代码的智能补全、跳转定义、悬停文档等功能。

## OHOS 适配

### 适配要点
- 纯 Python 项目，无需 C/C++ 编译
- 使用 setuptools 构建 wheel 包
- 从 PyPI tar.gz 下载时，setuptools_scm 无法自动检测版本，需静态指定版本号
- 运行依赖：json5、packaging（需预先安装）

### 已知问题
- 无 git 仓库时版本号显示为 0.0.0，需修改 `pyproject.toml` 将 `dynamic = ["version"]` 改为 `version = "3.2.2"`

## 依赖

### 编译依赖
- Python 3.7+
- setuptools >= 61
- wheel

### 运行依赖
- json5
- packaging

## 功能验证

```bash
fortls --version
# 输出: 3.2.2

fortls --help
# 显示命令行选项
```

## 参考

- 官网: https://fortls.fortran-lang.org
- 源码: https://github.com/fortran-lang/fortls
- PyPI: https://pypi.org/project/fortls/