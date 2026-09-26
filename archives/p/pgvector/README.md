# pgvector

## 简介

pgvector 是 PostgreSQL 的开源向量相似度检索扩展，提供 `vector` / `halfvec` / `sparsevec` / `bit`
四种向量类型，以及 `ivfflat`（倒排文件）与 `hnsw`（分层可导航小世界图）两种近似最近邻索引访问方法，
支持 L2 / 内积 / 余弦 / L1 / Hamming / Jaccard 等距离算子。常见用途是给 PostgreSQL 加上
RAG / 语义检索 / 推荐系统的向量召回能力。

## OHOS 适配

- 构建系统：PGXS（PostgreSQL Extension Building Infrastructure），无 configure 步骤，直接 `make`。
- 需要 PostgreSQL **服务端开发文件**（`pg_config` + PGXS makefile + `include/postgresql/server`），
  仅 libpq 客户端包装不下 —— 因此以 `tool_requires("postgresql/18.3")` 取用 ohpcd 制品仓中
  已发布并适配鸿蒙的 PostgreSQL 18.3（该包是完整 server+client 安装）。
- **零源码补丁**：上游源码在 OHOS（musl libc + clang 15 + PG 18.3 服务端头）下直接编译通过，
  `patches/` 不存在。
- 构建时仅调整两个上游/PGXS 文档化的 make 变量：`OPTFLAGS=`（去掉 `-march=native`，走上游
  portable 编译路径）与 `enable_rpath=`（避免把构建机的 PostgreSQL 包路径烤进模块 RUNPATH）。

## 产物与消费

```
lib/vector.so                        # PostgreSQL 可加载模块
extension/vector.control             # 扩展控制文件
extension/vector--*.sql              # 安装脚本 + 40 个增量升级脚本
```

安装到某个 PostgreSQL 前缀：

```bash
cp lib/vector.so        "$($PG_CONFIG --pkglibdir)/"
cp extension/*          "$($PG_CONFIG --sharedir)/extension/"
psql -c 'CREATE EXTENSION vector;'
```

## 依赖

- 构建期：`postgresql/18.3`（pg_config + PGXS + 服务端头 + 用于回归测试的服务端二进制）
- 运行期：无（模块只依赖 musl `libc.so`，PG 服务端符号由其自身提供）

## 测试

- 上游 pg_regress 用例组 **14/14** 逐字节通过（真实 PG 18.3 实例，TCP loopback，Unix socket 关闭）。
- 上游 Perl TAP 48 个脚本不可执行：依赖 Perl 模块 `IPC::Run`，OHOS 无此模块（已知限制）。
- 消费者断言 13/13（含鸿蒙特有 2、PC 特有 2），见 `0.8.6/reports/test-report.md`。

## 参考

- https://github.com/pgvector/pgvector
