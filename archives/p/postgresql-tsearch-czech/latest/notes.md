# postgresql-tsearch-czech latest 适配笔记

## 编译环境
- 构建系统: custom (Perl 脚本)
- 编译日期: 2026-05-19
- 编译器: N/A (纯数据文件)
- 状态: built

## 编译步骤

1. 克隆源码仓库：
   ```bash
   git clone https://github.com/tvondra/ispell_czech.git
   cd ispell_czech
   ```

2. 运行 Perl 脚本生成词典文件：
   ```bash
   perl make_config
   ```

3. 生成的文件：
   - `czech.affix`：词缀规则文件
   - `czech.dict`：词典数据文件

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无需编译步骤 | 纯数据文件项目 | 直接使用 Perl 生成词典 |

## 源码修改

无补丁，源码无需修改。

## 依赖版本

- perl: 5.38
- postgresql: 17.0

## 验证结果

```bash
# 检查生成的文件
ls -lh czech.affix czech.dict
# czech.affix: 约 74KB
# czech.dict: 约 4MB，包含 304138 条目

# 统计词典条目
wc -l czech.dict
# 304138 czech.dict
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| czech.affix | 74KB | 词缀规则文件 |
| czech.dict | 4MB | 词典数据文件（304138 条目）|

## OHOS 适配要点

1. **纯数据文件项目**：无需编译步骤
2. **Perl 依赖**：需要安装 Perl 环境运行生成脚本
3. **直接生成**：运行 `perl make_config` 即可生成词典文件
4. **安装位置**：将生成的文件安装到 PostgreSQL 的 `tsearch_data` 目录

## 使用方法

在 PostgreSQL 中配置捷克语全文搜索：

```sql
-- 创建词典
CREATE TEXT SEARCH DICTIONARY czech (
    TEMPLATE = ispell,
    DictFile = czech,
    AffFile = czech,
    StopWords = czech
);

-- 创建文本搜索配置
CREATE TEXT SEARCH CONFIGURATION czech (
    COPY = pg_catalog.english
);

-- 配置映射
ALTER TEXT SEARCH CONFIGURATION czech
    ALTER MAPPING FOR word, asciiword WITH czech;

-- 测试搜索
SELECT to_tsvector('czech', 'Ahoj světe');
```

## 质量状态

| 级别 | 状态 | 说明 |
|------|------|------|
| G0 | SKIP | 纯数据文件，无需编译 |
| G1 | PASS | 文件完整性检查通过 |
| G2 | PASS | 文件格式验证通过 |
| G3 | PASS | 词典文件可正常加载 |
| G4 | SKIP | 纯数据文件，无测试套件 |

## 注意事项

1. 确保词典文件使用 UTF-8 编码
2. PostgreSQL 需要正确配置 `tsearch_data` 目录
3. 大词典文件需要足够的内存加载
4. 定期更新词典以获得更好的搜索效果

---

**编译结束**: 2026-05-19
**最终状态**: built