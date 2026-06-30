# yamllint

## 软件简介

yamllint 是一个 YAML 文件语法检查工具，用于检测 YAML 文件的语法错误、格式问题和重复键等问题。

## 基本信息

- **官网**: https://github.com/adrienverge/yamllint
- **许可证**: GPL-3.0
- **编程语言**: Python
- **构建系统**: Python setuptools (custom)

## 功能特性

- 语法错误检测
- 格式风格检查（缩进、行长度等）
- 重复键检测
- 可配置的规则系统
- 支持自定义配置文件

## 依赖项

### 运行时依赖
- Python 3.9+
- pathspec >= 0.5.3
- pyyaml

### 编译依赖
- Python 3.9+
- setuptools

## 编译说明

### 编译步骤
1. 下载源码包
2. 解压源码
3. 使用 `pip install --prefix` 安装到目标目录
4. 打包预编译包

### 特殊说明
- 纯 Python 包，无需 configure/make
- 需要包含完整的 .egg-info 元数据目录
- 预编译包需要包含所有依赖（pathspec + pyyaml）

## OpenHarmony 适配

### 平台限制
- 无特殊平台限制
- 使用标准的 Python 安装方式

### 适配要点
1. 使用 `pip install --prefix=$HOME/usr/local .` 安装
2. 确保生成 .egg-info 元数据目录
3. 预编译包需包含依赖：pathspec、pyyaml、libyaml

### 测试验证
```bash
# 版本验证
yamllint --version

# 功能测试
yamllint test.yaml
```

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 1.37.1 | built | 2026-05-20 |

## 相关资源

- [yamllint 官方文档](https://yamllint.readthedocs.io/)
- [yamllint GitHub 仓库](https://github.com/adrienverge/yamllint)