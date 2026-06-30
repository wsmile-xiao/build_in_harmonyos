# pgcli

> pgcli — PostgreSQL 命令行客户端，自动补全和语法高亮

## 简介

pgcli 是一个 PostgreSQL 的命令行客户端，具有自动补全和语法高亮功能。它使用 prompt_toolkit 库提供智能补全，让与 PostgreSQL 数据库的交互更加高效。

## OHOS 适配要点

- 纯 Python 项目，使用 pip install 方式安装
- pip --target 安装后需修复脚本 shebang（改为 `#!/usr/bin/env python3`）
- setproctitle C 扩展 .so 文件需要 ELF 签名

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python 3 | 3.12.8 | 运行时依赖 |
| click | 8.4.1 | CLI 依赖 |
| prompt_toolkit | 3.0.52 | UI 依赖 |
| psycopg | 3.3.4 | PostgreSQL 连接 |

## 功能验证

```bash
pgcli --version
```

## 参考

- [官方文档](https://www.pgcli.com/)
- [源码仓库](https://github.com/dbcli/pgcli)
