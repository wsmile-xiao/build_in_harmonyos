# psql2csv 1.1.4 适配笔记

## 编译环境
- 构建系统: custom (shell/pip)
- 编译日期: 2026-06-12
- 编译器: N/A (Python 包)
- 状态: built

## 编译步骤
```bash
# 1. 下载源码
wget https://github.com/joeyism/psql2csv/archive/refs/tags/1.1.4.tar.gz
tar -xzf 1.1.4.tar.gz

# 2. pip 安装
pip install psql2csv-1.1.4.tar.gz --target $HOME/usr/local/lib/python3

# 3. 或手动安装
cp -r psql2csv/ $HOME/usr/local/lib/python3/site-packages/
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CLI 执行 Permission denied | psycopg2/_psycopg.so 需 OHOS ELF 签名 | 对 psycopg2.so 执行 ELF 签名 |
| 2 | PostgreSQL 连接不可用 | 测试环境无 PostgreSQL 服务 | 需部署 PostgreSQL 后才能进行功能测试 |

## 依赖版本
- Python 3.x（已预装）
- psycopg2（需 ELF 签名后才能运行）

## 验证结果
- Python 模块导入 ✅ `import psql2csv; print(psql2csv.__version__)` → "1.1.4"
- 模块结构 ✅ cli.py 导入正确，核心模块加载
- CLI 执行 ❌ psycopg2 ELF 签名问题
- PostgreSQL 连接 ⚠️ 需运行服务器

## 交付物
| 文件 | 说明 |
|------|------|
| psql2csv-1.1.4-ohos-aarch64.tar.gz | 主包 |
| psql2csv-1.1.4-ohos-aarch64-debug.tar.gz | debug 包 |

## 注意事项
- CLI 执行需要对 psycopg2 进行 ELF 签名
- 这是平台限制，不是编译问题
- 功能测试需要实际 PostgreSQL 连接