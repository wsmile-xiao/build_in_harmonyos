# Alembic (Python 3)

> Database migration tool for SQLAlchemy

## 简介

py3-alembic 是 SQLAlchemy 的数据库迁移工具，用于管理数据库 schema 的变更。支持版本控制、升级/降级迁移脚本生成、自动检测 schema 变化等功能。

## OHOS 适配要点

- 纯 Python 包，无需源码修改
- 使用 pip/setuptools 标准安装流程

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| python3 | 3.x | Python 运行时 |
| py3-sqlalchemy | 2.x | SQLAlchemy ORM |

## 功能验证

```bash
python3 -c "import alembic; print(alembic.__version__)"
```

## 参考

- [Alembic 官网](https://alembic.sqlalchemy.org/)
- [PyPI: alembic](https://pypi.org/project/alembic/)
