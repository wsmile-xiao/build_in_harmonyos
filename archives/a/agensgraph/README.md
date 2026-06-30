# AgensGraph

AgensGraph is a multi-model graph database based on PostgreSQL 13.8, supporting both SQL and Cypher query languages.

## 简介

AgensGraph 是基于 PostgreSQL 的多模型图数据库，支持关系型数据和图数据的统一存储与查询。

## OHOS 适配

### 适配要点

1. **平台识别 (E072)**: 需要替换 config.guess 和 config.sub 为最新版本以支持 OHOS 平台三元组 `aarch64-unknown-linux-ohos`

2. **HMDFS 权限问题 (E011)**: configure 脚本中的 `umask 077` 会导致临时目录无法写入，需修改为 `umask 022`

3. **单线程编译**: HMDFS 不支持 mkfifo 操作，需使用 `make -j1` 进行单线程编译

4. **预编译包打包**: HMDFS 的 ustar 格式不支持长路径，预编译包需使用 zip 格式而非 tar.gz

### 已知问题

- 功能测试受限（平台 Python subprocess 限制）
- G0 干净构建验证需手动执行

### 与 Linux 的差异

- 编译时需设置 `LD_LIBRARY_PATH` 以确保 readline 等依赖库可被找到
- 预编译包格式为 zip（而非 tar.gz）

## 依赖

### 编译依赖
- readline 8.2

### 运行依赖
- readline 8.2（已包含在预编译包中）

## 功能验证

### 基本功能
```bash
# 初始化数据库
initdb -D /path/to/data

# 启动服务
ag_ctl start -D /path/to/data

# 连接数据库（支持 Cypher 查询）
agens -d database_name

# 执行图查询
SELECT * FROM cypher('graph_name', $$
  MATCH (n) RETURN n
$$) as (n agtype);
```

## 排除与替代

无特殊排除项。

## 参考

- 官网: https://bitnine-oss.github.io/agensgraph/
- GitHub: https://github.com/bitnine-oss/agensgraph
- 文档: https://bitnine-oss.github.io/agensgraph-docs/
