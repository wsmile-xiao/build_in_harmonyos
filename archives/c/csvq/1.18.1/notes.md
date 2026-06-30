# csvq 1.18.1 适配笔记

## 编译环境
- 构建系统: go
- 编译日期: 2026-06-12
- 编译器: go1.26.0 linux/arm64
- 状态: built

## 编译步骤
```bash
# 1. 下载源码
wget https://github.com/mithrandie/csvq/archive/refs/tags/v1.18.1.tar.gz
tar -xzf v1.18.1.tar.gz
cd csvq-1.18.1

# 2. Go 编译
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o $HOME/usr/local/bin/csvq .

# 3. ELF 签名
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf $HOME/usr/local/bin/csvq
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go 链接器权限错误 | HMDFS 文件系统限制 | 首次编译成功（缓存复用），与 kustomize 等其他 Go 项目相同 |

## 依赖版本
- Go 1.26.0

## 验证结果
- csvq --version = "csvq version 1.18.1" ✅
- csvq --help ✅（显示 SQL-like query language for csv）
- SELECT * FROM people WHERE age > 28 ✅（返回2行正确结果）
- SELECT COUNT(*), AVG(age) FROM people ✅（cnt=4, avg_age=29.5）
- CSV 文件读取 ✅（支持 header）
- SQL 查询解析 ✅（WHERE、ORDER BY、聚合函数）

## 交付物
| 文件 | 说明 |
|------|------|
| csvq-1.18.1-ohos-aarch64.tar.gz | 主包 |
| csvq-1.18.1-ohos-aarch64-debug.tar.gz | debug 包 |

## 注意事项
- 无正式测试套件（Go 项目无 make check）
- Go 链接器 HMDFS 限制同其他 Go 项目（kustomize 等）