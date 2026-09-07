# pgdbf

将 XBase / dBase / FoxPro DBF 文件转换为 PostgreSQL 可导入的 SQL 格式。

- 上游: http://pgdbf.sourceforge.net/
- 许可: GPL-3.0-or-later
- 构建: autotools (configure + make)，产物为单个命令行工具 `pgdbf`
- HarmonyOS PC (aarch64, OHOS) 适配版本: 0.6.2

## 用法示例

```bash
# 生成含 CREATE TABLE / COPY 的导入 SQL
pgdbf data.dbf > data.sql

# DBF 内字符集为 LATIN1 时转成 UTF-8 输出
pgdbf -s LATIN1 data.dbf > data-utf8.sql
```

## 归档

- `0.6.2/conanfile.py` — Conan 配方（application, autotools）
- `0.6.2/test_package/` — 消费者功能测试（dBase III 样例转换断言）
- `commands.json` — hicmd 命令行工具声明
