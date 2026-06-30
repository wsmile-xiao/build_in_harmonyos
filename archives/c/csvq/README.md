# csvq

## 简介
csvq 是一个使用 Go 语言实现的 CSV 文件 SQL 查询工具，支持 SQL 语法对 CSV 文件进行查询、筛选、排序和聚合操作。

## OHOS 适配
- Go 语言项目，使用标准 Go 构建流程（CGO_ENABLED=0 go build）
- 无补丁，源码无需修改即可在 HarmonyOS 上编译运行
- Go 链接器在 HMDFS 文件系统上可能有权限问题（同其他 Go 项目）
- 无正式测试套件（Go 项目无 make check）

## 依赖
- Go >= 1.21（编译时依赖）
- 无运行时依赖

## 功能验证
```bash
# 版本检查
csvq --version
# 输出: csvq version 1.18.1

# 基本查询
csvq "SELECT * FROM people WHERE age > 28" /path/to/people.csv

# 聚合查询
csvq "SELECT COUNT(*), AVG(age) FROM people" /path/to/people.csv

# 显示帮助
csvq --help
```

## 参考
- GitHub: https://github.com/mithrandie/csvq