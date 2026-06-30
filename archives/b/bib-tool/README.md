# bib-tool

## 软件信息

- **软件名称**: bib-tool (BibTool)
- **描述**: Manipulates BibTeX databases - A powerful tool for manipulating BibTeX bibliographies
- **官方地址**: https://ctan.org/pkg/bibtool
- **许可证**: GPL

## 功能特性

BibTool 是一个功能强大的 BibTeX 数据库处理工具，主要功能包括：

- **格式化与规范化**: 将 BibTeX 条目重新格式化为标准形式
- **排序**: 按多种条件对条目进行排序（作者、年份、关键字等）
- **搜索与过滤**: 根据字段内容筛选条目
- **字段操作**: 添加、删除、重命名字段
- **字符串管理**: 管理 @string 宏定义
- **交叉引用处理**: 自动处理交叉引用关系
- **重复检测**: 识别和处理重复条目

## 已发布版本

| 版本 | 状态 | 构建系统 | 发布日期 | 补丁数 | 详情 |
|------|------|----------|----------|--------|------|
| 2.68 | ✅ 已发布 | makefile | 2026-06-06 | 0 | [查看](./2.68/) |

## 技术说明

- **构建系统**: Makefile (基于 makefile.unx)
- **编译器**: clang/clang++
- **依赖**: 无外部依赖（内嵌 regex-0.12 库）
- **平台**: OpenHarmony ARM64

## 使用说明

### 基本用法

```bash
# 格式化 BibTeX 文件
bibtool input.bib > output.bib

# 按作者排序
bibtool -s input.bib > sorted.bib

# 筛选特定作者的条目
bibtool -- 'select{author "Smith"}' input.bib

# 提取特定年份的文献
bibtool -- 'select{year 2023}' input.bib
```

### 注意事项

- bib-tool 不支持 `--version` 或 `--help` 参数
- 使用 K&R 风格的 C 代码，编译时会有警告但不影响功能
- 完整功能需要通过处理 BibTeX 文件来验证

## 编译质量

所有版本都经过严格的质量门禁验证（G1-G4）：

- ✅ G1: 二进制完整性
- ✅ G2: 功能可用性
- ✅ G3: 可移植性（RPATH/签名）
- ✅ G4: 档案完整性

## 相关链接

- [CTAN BibTool 页面](https://ctan.org/pkg/bibtool)
- [官方文档](https://ctan.org/pkg/bibtool)
- [版本 2.68 详细编译笔记](./2.68/notes.md)