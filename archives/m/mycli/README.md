# mycli

## 简介
mycli 是一个 MySQL 命令行客户端，具有自动补全和语法高亮功能。它兼容 MySQL、MariaDB、Percona、TiDB 和 Doris。

## 依赖
- Python 3.10+ (系统预装 3.12.8)
- click、Pygments、prompt_toolkit、PyMySQL、sqlparse、configobj、wcwidth 等纯 Python 依赖
- cryptography（系统预装 44.0.0，mycli 期望 46+）

## OpenHarmony 适配要点
- 纯 Python 项目，使用 pip 安装到 staging 目录后打包
- 无传统 autotools/cmake 构建系统
- 需要设置 SETUPTOOLS_SCM_PRETEND_VERSION 环境变量（GitHub tarball 缺少 git 元数据）
- cryptography 依赖版本冲突：mycli 要求 ~=46.0.5 但系统只有 44.0.0
- 无 ELF 二进制文件，无需签名/strip/RPATH 处理

## 版本历史
| 版本 | 状态 | 日期 |
|------|------|------|
| 1.74.0 | built | 2026-06-09 |