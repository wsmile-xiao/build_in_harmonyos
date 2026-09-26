# pgvector 0.8.6 适配笔记（OHOS PC aarch64）

## 一句话

PostgreSQL 向量检索扩展（`vector` / `halfvec` / `sparsevec` / `bit` 类型 + `ivfflat` / `hnsw` 索引）。
使用上游 PGXS 构建系统，**零源码补丁**（`patches/` 不存在），制品包为可加载模块 `lib/vector.so`
+ `extension/`（`vector.control` + 41 个版本 SQL）。

## 上游信息

| 项 | 值 |
|----|----|
| 上游仓库 | https://github.com/pgvector/pgvector |
| 版本 / tag | 0.8.6 / `v0.8.6` |
| tarball | https://github.com/pgvector/pgvector/archive/refs/tags/v0.8.6.tar.gz |
| sha256 | `10bf9938906e5d643bbc4a7eea104b6f57ba4898e5b76b20e60484ea1d5a7f8f` |
| 语言 / 构建系统 | C / PGXS（PostgreSQL Extension Building Infrastructure） |

## W0：依赖核查（结论：依赖已发布，走 PGXS 全套）

- `conan list "*postgres*" -r=ohpcd` → 命中 7 条配方：`autopostgresqlbackup/2.5`、`postgresql/16.10`、
  `postgresql/18.3`、`postgresql-hypopg/1.4.2`、`postgresql-pllua/2.0.12`、
  `postgresql-sequential-uuids/1.0.3`、`postgresql-topn/2.7.0`；仓内 `archives/p/` 另有 14 个 `postgresql*`
  归档目录（其中 13 个是 PG 扩展）可作约定参照。
- `conan download postgresql/18.3 -r=ohpcd --only-recipe` + `conan install --requires=postgresql/18.3`
  （R35：用 download/install 而非 list 判 binary）→ 二进制包 10.5 MB 实际拉取成功。
- 解开包核对（`conan cache path`）：`bin/pg_config`、`lib/postgresql/pgxs/src/makefiles/pgxs.mk`、
  `include/postgresql/server/`、`include/postgresql/internal/`、`share/postgresql/extension/`、
  `bin/{postgres,initdb,pg_ctl,createdb,psql}` **全部齐备** —— 即一个完整的 server+client 安装。
- 因此本库**不需要 vendored PostgreSQL 源码树**（对照：同仓 `postgresql-topn/2.7.0`、
  `postgresql-sequential-uuids/1.0.3` 因为在 PG 制品包发布之前适配，各自把 PG 18.3 源码连同
  `0001-postgresql-harmony.patch` 一起塞进了自己的归档）。本归档 `patches/` 不存在，也**没有**
  携带任何第三方补丁。
- W0 双查（D1）：`git ls-tree -r --name-only origin/main archives/p/pgvector` → 无输出，main 上无他人同库归档，无撞车。

## 构建

```bash
# PGXS：无需 configure，直接 make；配方内实际执行
make PG_CONFIG="<postgresql/18.3 包>/bin/pg_config" OPTFLAGS= enable_rpath= -j20
```

三个 make 变量的理由（均为上游 / PGXS 文档化参数，**无源码改动**）：

| 变量 | 理由 |
|------|------|
| `PG_CONFIG=<abs>` | PGXS 经 `$(shell $(PG_CONFIG) --pgxs)` 定位 makefile 片段；用 tool_requires 贡献的绝对路径，避免 PATH 歧义 |
| `OPTFLAGS=` | 上游 Makefile 注释即写明 `# To compile for portability, run: make OPTFLAGS=""`。默认 `-march=native` 会把产物绑定到**构建机**的 CPU 特性；制品要发布给全部 OHOS PC aarch64 设备，走上游 portable 路径 |
| `enable_rpath=` | PGXS 的 `Makefile.global` 有 `LDFLAGS += $(rpath)`（`rpathdir = $(libdir)`），会把构建机的 `<postgresql 包>/lib` **烤进模块 RUNPATH**。该模块只需要 libc，去掉后产物可重定位（实测 `readelf -d`：只剩 `NEEDED libc.so`，无 RUNPATH） |

编译产物（实测）：`vector.so` 203200 字节，`NEEDED libc.so` 唯一，无 SONAME（dlopen 型模块，非链接库），
含 `.codesign` 段（鸿蒙 PC ELF 加载签名段，链接器自动生成，**未做任何链接后改写**）。

## 打包布局

```
archives/p/pgvector/0.8.6/
├── conanfile.py            # 配方
├── conandata.yml           # 官方 tarball + sha256（R39）
├── test_package/           # 消费者测试入口 + 断言执行体 + MANIFEST.yml
├── manifest.yaml           # 本文件同级：编译元数据
├── notes.md                # 本文件
└── reports/test-report.md  # 验证报告
```

包内布局：

```
lib/vector.so                        # 可加载模块（pkglibdir 对应物）
extension/vector.control             # 扩展控制文件
extension/vector--0.8.6.sql          # 安装脚本（上游 Makefile 由 sql/vector.sql 生成）
extension/vector--x.y.z--a.b.c.sql   # 40 个增量升级脚本
upstream/test/{sql,expected}/        # 上游回归资产（14 组 sql + out），供消费者 harness 执行
licenses/LICENSE
```

`package_info()` 按本仓其它 PG 扩展配方的惯例声明 `cpp_info.libs = ["vector"]`（`libdirs = ["lib"]`、
`resdirs = ["extension"]`）。需注意语义：`vector.so` 是 PostgreSQL 的**可加载模块**，由服务端经
`$libdir/vector` dlopen 加载，本身**无 SONAME**、且刻意保留对 PG 服务端符号的未定义引用 —— 它不是
给下游链接用的库。真正的消费接口是：`lib/vector.so` → `$(pg_config --pkglibdir)`，
`extension/*` → `$(pg_config --sharedir)/extension`（对照 `test_package/pgvector_test.py` 的实际装载方式）。

## 测试

### 上游测试资产清点（实测）

| 类型 | 数量 | 来源 |
|------|------|------|
| pg_regress 用例组 | 14 | `Makefile: REGRESS = $(patsubst test/sql/%.sql,%,$(wildcard test/sql/*.sql))`，每组配套非空 `test/expected/<name>.out` |
| Perl TAP 脚本 | 48 | `test/t/*.pl`（`prove` + `PostgreSQL::Test::Cluster`） |

### 实测结果

- **pg_regress 14/14 逐字节通过**。pg_regress 的实际口径是
  `psql -X -a -q -d <db>` **从 stdin 读脚本**、把 stdout+stderr 合并后与 `test/expected/<name>.out`
  **逐字节**比较（`copy.sql` 还要求 cwd 下有可写的 `results/`，因为脚本里写的是相对路径
  `\copy t TO 'results/vector.bin'`）。harness 完全复刻这一调用形态，因此与官方 pg_regress 结果等价。
  - **坑（实测）**：若改用 `psql -f <file>`，psql 会给报错加 `psql:<file>:<line>:` 前缀，
    13/14 组会"假失配"（错误信息内容其实完全一致）。必须走 stdin。
  - **pg_regress 二进制不在 `postgresql/18.3` 制品包里**（包的 bin/ 只有 35 个工具，无 pg_regress），
    而自行构建 pg_regress 意味着把 PostgreSQL 源码树 vendor 进本归档 —— 不划算，故采用上述等价驱动。
- **48 个 TAP 脚本未执行**，如实归因：`PostgreSQL::Test::Cluster` 依赖 Perl 模块 **IPC::Run**，
  OHOS perl 5.42 的 `@INC` 里没有该模块（`perl -MIPC::Run -e1` → `Can't locate IPC/Run.pm`），
  也没有可宣称的 conan 依赖可补，CI 干净环境同样不具备 → 平台不可落地，记为已知限制。
- 消费者 harness 13 项断言全过（详见 `reports/test-report.md`）。

### 免拷贝加载扩展（PG 18 机制）

harness 不往 `postgresql/18.3` 安装目录写任何文件，而是用两个 PG 18 服务端参数把包目录本身
变成扩展来源：

```
extension_control_path = '<pkg>:$system'          # PG 查 <path>/extension/<name>.control
dynamic_library_path   = '<pkg>/lib:$libdir'      # 模块解析
```

实测确认模块确实从包目录加载（`find .conan2 -name vector.so` 在包缓存中无任何副本）。
注意 `extension_control_path` 的每个路径项应是 **share 目录**（PG 自己拼 `/extension`），
填到 `extension/` 一层会找不到控制文件（踩过）。

### 平台行为

- 服务端只能走 **TCP loopback**：OHOS 的 Unix domain socket `bind()` 返回 EPERM，因此
  `unix_socket_directories=''`、`listen_addresses='127.0.0.1'`。整个 harness（initdb → 启动 →
  `CREATE EXTENSION` → 建索引 → 查询 → 14 组回归）全部在此配置下跑通。
- initdb 在 OHOS 上可直接运行（`--no-locale -E UTF8 -A trust`），数据页校验和默认开启。

## 已知限制

1. **48 个 TAP 测试不可执行**（缺 Perl IPC::Run），原因见上；非平台缺陷、非适配缺陷。
2. harness 不使用 pg_regress 二进制而是等价复刻其 psql 调用与逐字节比对；比对差异 0，
   故报告为"上游 pg_regress 用例组 14/14"。
3. 未做真机多设备分发验证：`-march=native` 已按上游 portable 路径关闭，其余为纯 C + libc。
4. 扩展的 `hash` 索引/`<#>`(负内积) 等高级特性依赖 PG 版本语义，本包以 PG 18.3 头文件编译，
   与 PG 18.3 服务端 ABI 对齐（PG 扩展的 ABI 与服务端大版本绑定）。
