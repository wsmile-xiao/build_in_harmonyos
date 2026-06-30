# postgresql-tsearch-czech

PostgreSQL 捷克语全文搜索词典，基于 Ispell/Hunspell 格式。提供高质量的捷克语词形还原和词干提取功能。

## 描述

该项目提供 PostgreSQL 全文搜索所需的捷克语词典文件：
- 支持捷克语的词形还原（lemmatization）
- 支持 Ispell/Hunspell 词典格式
- 纯数据文件项目，无需编译
- 使用 Perl 脚本生成词典数据

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| latest | built | 2026-05-19 |

## 特点

1. **纯数据文件**：无需编译，直接生成词典文件
2. **Hunspell 格式**：兼容标准的 Hunspell 词典格式
3. **高质量词典**：包含 30 万+ 词条

## 编译说明

使用 Perl 脚本生成词典文件：
```bash
perl make_config
```

生成的文件：
- `czech.affix`：词缀规则文件（约 74KB）
- `czech.dict`：词典数据文件（约 4MB，304138 条目）

## OHOS 适配

1. 需要安装 Perl 环境
2. 直接运行生成脚本，无需编译步骤
3. 将生成的词典文件安装到 PostgreSQL 的 tsearch_data 目录

## 使用方法

在 PostgreSQL 中配置：
```sql
CREATE TEXT SEARCH DICTIONARY czech (
    TEMPLATE = ispell,
    DictFile = czech,
    AffFile = czech,
    StopWords = czech
);

CREATE TEXT SEARCH CONFIGURATION czech (
    COPY = pg_catalog.english
);

ALTER TEXT SEARCH CONFIGURATION czech
    ALTER MAPPING FOR word, asciiword WITH czech;
```

## 注意事项

1. 确保词典文件正确安装到 PostgreSQL 的数据目录
2. 词典文件编码应为 UTF-8
3. 需要足够的内存加载大词典文件

## 参考

- GitHub: https://github.com/tvondra/ispell_czech
- PostgreSQL 文档: https://www.postgresql.org/docs/current/textsearch-dictionaries.html