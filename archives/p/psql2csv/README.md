# psql2csv

## 简介
psql2csv 是一个将 PostgreSQL 查询结果导出为 CSV 格式的 Python 工具，可以方便地从 PostgreSQL 数据库提取数据并转换为 CSV 文件。

## OHOS 适配
- Python 包，使用 pip install 或手动安装
- Python 模块导入正常（`import psql2csv` → 版本 1.1.4）
- CLI 执行受 OHOS ELF 签名限制：psycopg2/_psycopg.so 需 ELF 签名才能运行
- 这是平台限制，不是编译问题

## 依赖
- Python >= 3.x
- psycopg2（PostgreSQL Python 驱动，需 ELF 签名）
- PostgreSQL 服务器（运行时依赖）

## 功能验证
```bash
# Python 模块导入测试
python3 -c "import psql2csv; print(psql2csv.__version__)"
# 输出: 1.1.4

# CLI 执行（需要 psycopg2 ELF 签名和 PostgreSQL 连接）
psql2csv --help
# 注意：当前因 ELF 签名问题 CLI 无法直接运行

# 导出查询结果（需要运行 PostgreSQL 服务器）
psql2csv "SELECT * FROM table_name" database_name -o output.csv
```

## 已知限制
- CLI 执行需要 psycopg2 的 ELF 签名（OHOS 安全机制）
- 功能测试需要运行 PostgreSQL 服务器

## 参考
- GitHub: https://github.com/joeyism/psql2csv