# PGXS 扩展 OHOS 适配 — 处理策略与配方模板

> 知识库条目：`PGXS-EXTENSION-OHOS-ADAPTATION`
> 样例库：pg-crash/0.3（`archives/p/pg-crash/0.3`）
> 检测脚本：`detect_pgxs.py`（同目录）

## 适用场景（一类问题，非单库补丁）

上游构建文件命中以下任一特征：

```make
PGXS := $(shell $(PG_CONFIG) --pgxs)
include $(PGXS)
```

且 C 源包含服务端头（`postgres.h` / `fmgr.h` / `PG_MODULE_MAGIC`）。
同一形态覆盖：pg_crash、pgvector、pg_cron、pg_repack、pgq/pgqd、
pgfincore、pg-ivm、pg-gvm、pglogical 等 PostgreSQL 扩展家族。

## 根因

PGXS 扩展的编译由 **postgresql 服务端开发树** 驱动：`pg_config` 提供
编译器、CFLAGS、头路径（`--includedir-server`）、PGXS makefile 路径
（`--pgxs`）。普通 libpq 客户端包不够；扩展翻译单元硬包含服务端头，
离线手工拼 `-I` 不可维护。OHOS 上没有系统 postgresql，必须把 conan
发布的 postgresql 包当作"服务端开发树"接入 PGXS。

## 处理策略（配方模板，与样例一一对应）

### 1. 依赖接入：`tool_requires`，不 require

```python
def build_requirements(self):
    self.tool_requires("postgresql/16.10")   # 或 18.3
```

`tool_requires` 而非 `requires`：扩展产物是服务端 dlopen 的模块，
不由消费者链接；postgresql 只在构建期/测试期需要。

### 2. 构建：PG_CONFIG 注入 + 关 rpath

```python
def build(self):
    pg_config = self._pg_config()          # 从 tool_requires 包里解析
    self.run(f'make PG_CONFIG="{pg_config}" enable_rpath=',
             cwd=self.source_folder)
```

* `PG_CONFIG="<abs path>"` — PGXS 的唯一强制入口；
* `enable_rpath=` — 防 PGXS 把构建机的 `<postgresql>/lib` 烤进模块
  RUNPATH（Makefile.global: `LDFLAGS += $(rpath)`），保持制品可重定位；
* 编译器由 `pg_config --cc` 提供（构建 postgresql 包用的同一 OHOS
  clang），配方不需要也不应该再注入 `CC`。

### 3. 打包：只收模块与扩展资产

```python
copy(self, "*.so", self.source_folder, os.path.join(pkg, "lib"))
copy(self, "*.control", self.source_folder, os.path.join(pkg, "extension"))
copy(self, "*--*.sql",  self.source_folder, os.path.join(pkg, "extension"))
```

注意：`MODULE_big` 型扩展（如 pg_crash）上游可能**没有**
EXTENSION/DATA 规则——tarball 里没有 `.control`/`.sql`，此时只打包
`lib/*.so`（加载方式为 `shared_preload_libraries`），不要虚构 control
文件。检测：Makefile 无 `EXTENSION =` 行即属此类。

### 4. package_info

```python
self.cpp_info.libs = ["<module_name>"]   # 无 SONAME 的 dlopen 模块
self.cpp_info.libdirs = ["lib"]
# 有 extension/ 资产时：self.cpp_info.resdirs = ["extension"]
```

### 5. settings 兼容

OHOS profile 声明 `os.version=6.0`，postgresql 配方未声明该 setting：
配方里 `self.settings.rm_safe("os.version")`（照抄 pgvector/pg-crash）。

## 验证（消费者链路）

无 `.control` 的 preload 型扩展：

1. `initdb` 起一次性集群，`postgresql.auto.conf` 写
   `dynamic_library_path = '<pkg>/lib:$libdir'` +
   `shared_preload_libraries = '<module>'`；
2. `pg_ctl start` 后断言：`_PG_init` 注册的 GUC `SHOW` 可见、
   `pg_stat_bgworker` 可查 worker、server.log 有模块启动 LOG；
3. 测试期把会杀进程的参数置无害值（如 `crash.signals='0'`、
   `crash.delay=3600`）。

有 `.control` 的 CREATE EXTENSION 型扩展：参照 pgvector/0.8.6 的
`extension_control_path` + `CREATE EXTENSION` + 上游 pg_regress 套件。

## 禁止行为

* ❌ 把 postgresql 源码树 vendoring 进扩展包（用 `tool_requires`）；
* ❌ 手工 `-I<pg>/include/server` 绕过 PGXS（头路径由 pg_config 给出，
  本仓布局是 `include/postgresql/server`，手拼极易错）；
* ❌ 保留 PGXS 默认 rpath（制品带上构建机路径，破坏可重定位）；
* ❌ 给无 control 的模块虚构 `.control`/`.sql`。

## 边界

* 扩展若用 `PGXS` 之外的安装钩子（`install-` 自定义目标）需要逐一核对；
* 需要运行期验证的扩展依赖一个**能在 OHOS 上跑的 postgres**（本仓
  postgresql/16.10 已发布全套 server 二进制，initdb/pg_ctl/psql 可用）；
* 钩入内核接口的扩展（如 fdw 依赖外部守护进程）超出本模板范围。
