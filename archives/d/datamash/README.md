# GNU datamash

## 简介

GNU datamash 是一个命令行数据处理工具，用于对文本数据执行统计和数值操作。它设计为与 GNU coreutils 和其他标准 Unix 工具协同工作，支持管道操作和文本流处理。

## 功能特性

- **统计操作**：sum、mean、median、mode、min、max、range、variance、stddev 等
- **计数操作**：count、unique、first、last 等
- **文本处理**：transpose、reverse、sort 等
- **分组计算**：支持按字段分组执行操作
- **交叉表**：crosstab 功能用于生成交叉表
- **辅助工具**：decorate 命令用于装饰和排序文本行

## 典型用法

```bash
# 计算数值总和
echo "1 2 3 4 5" | datamash sum 1
# 输出: 15

# 计算平均值
echo "1 2 3 4 5" | datamash mean 1
# 输出: 3

# 统计行数
echo -e "a\nb\nc" | datamash count 1
# 输出: 3

# 分组求和
echo -e "group1 10\ngroup1 20\ngroup2 15\ngroup2 25" | datamash -g 1 sum 2
# 输出: group1 30
#       group2 40

# 交叉表
echo -e "A X 1\nA Y 2\nB X 3\nB Y 4" | datamash crosstab 1,2 sum 3
# 输出: X	Y
#       A	1	2
#       B	3	4
```

## 相关链接

- 官方网站: https://www.gnu.org/software/datamash/
- 手册: https://www.gnu.org/software/datamash/manual/
- 下载: https://ftp.gnu.org/gnu/datamash/

## 编译版本

- 版本: 1.9
- 发布日期: 2025-04-04
- 平台: HarmonyOS aarch64
- 编译日期: 2026-06-09