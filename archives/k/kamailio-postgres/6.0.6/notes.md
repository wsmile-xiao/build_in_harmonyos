# kamailio-postgres 6.0.6 适配笔记（OHOS PC / aarch64-linux-ohos）

## 一、基本信息

| 项 | 值 |
|---|---|
| 包名 / 版本 | `kamailio-postgres/6.0.6` |
| 发行版子包口径 | Alpine `kamailio-postgres`（`pkg/kamailio/alpine/APKBUILD:255` `_mod_list_postgres="db_postgres"`；`postgres()` 调 `_db_driver Postgres postgres postgres pgsql`） |
| 上游工程 | Kamailio SIP Server 6.0.6（<https://github.com/kamailio/kamailio>，官网 <https://www.kamailio.org>） |
| 交付产物 | `lib/kamailio/modules/db_postgres.so`（+ `licenses/COPYING`） |
| 构建系统 | kamailio 经典 Makefile 体系（`src/Makefile` + `Makefile.defs` + `Makefile.modules`） |
| 语言 | C（R47 lang-preflight：detected=cpp，c↔cpp 兼容族） |
| 依赖 | `libpq/18.6.1`（仅客户端库；模块 `NEEDED` 为 `libpq.so.5` + `libc.so`） |
| 补丁 | **0 个**（源码包原生识别 `aarch64-unknown-linux-ohos`，`patches: {}`） |
| 状态 | built（本机 conan create 全绿） |

## 二、打包口径

- 取官方源码包全量源码，**只编译打包 db_postgres 一个模块**，不构建 kamailio 主程序；
  模块 `.so` 由 kamailio 运行时 `loadmodule "db_postgres.so"` 加载，故不作为链接库供消费者使用
  （`package_info` 只声明 `lib/kamailio/modules` 目录与 `kamailio_modules_dir` 属性）。
- 与同族 `kamailio-unixodbc/6.0.6` 完全一致的目录/元数据布局（软件级 `README.md`、版本级
  `manifest.yaml`/`notes.md`/`conandata.yml`/`conanfile.py`/`test_package/`）。
- Alpine 子包还会 `mv` kamctl 的 postgres 脚本（`share/kamailio/postgres`、
  `lib/kamailio/kamctl/*.pgsql`）到子包；本包与同族 conan 包保持一致，只交付模块 `.so`
  与许可证（配置脚本属部署侧内容，未纳入制品）。

## 三、构建要点与踩坑

1. **必须先 `make cfg`**：`make cfg include_modules=db_postgres` 生成 `src/config.mak`，
   否则 `make modules` 报 `No rule to make target 'cfg-defs'`。
2. **libpq 探测分支必须钉死**：`src/modules/db_postgres/Makefile` 依次尝试
   ① `pkg-config --exists libpq` ② `PGCFG=$(shell which pg_config)` ③ `LOCALBASE/SYSBASE`
   回退。构建机若存在系统 libpq 的 pkg-config 或 `pg_config`，会被自动探测命中并注入宿主
   include/lib 路径 → 必须显式传 `LIBPQ_BUILDER=` 与 `PGCFG=`（make **命令行**变量优先级
   高于 Makefile 内部赋值）钉死 ③ 回退分支，并以 `LOCALBASE=<libpq 包目录>` 提供正确路径；
   同时用 `CPATH`/`LIBRARY_PATH` 环境兜住头/库搜索（R33：不用未定义的 shell 变量）。
3. **并行度固定 `-j1`**（E525/E074）：OHOS SELinux 禁止用户进程创建 FIFO，GNU make
   jobserver 靠 FIFO 传递令牌，`-j>1` 有挂起/报错风险；与同族 kamailio-* 配方一致。
4. **产物形态**：`db_postgres.so` 为 `ET_DYN` + AArch64，`NEEDED = libpq.so.5, libc.so`，
   无 RPATH/RUNPATH，且带 `FLAGS_1=DF_1_NOW`（BIND_NOW）——这与 OHOS/musl 加载器
   **不做惰性绑定**的行为一致：模块加载时全部未定义符号必须立即可解析。

## 四、上游测试清点与真实执行（R51 三步法）

### 1. 清点（源码包文档级全量清点，N=17）

```
$ tar tzf kamailio-6.0.6_src.tar.gz | grep -cE "/test/"
10        # 其中 utils/kamctl/dbtextdb/tests/ 下 10 个为用例数据
$ tar tzf … | grep -E "/test/" | grep -v dbtextdb
kamailio-6.0.6/src/modules/janssonrpcc/test/{run-tests.sh,mem-test.sh,test.cfg}
kamailio-6.0.6/src/modules/rtpproxy/test/{kamailio.cfg,exec_rtpproxy.txt,exec_pjsua.txt}
kamailio-6.0.6/src/modules/tm/test/kill_sem.sh
```

- 清点面 = 官方源码包内 `test/`、`tests/` 目录：4 个目录 / **17 个文件**
  （dbtextdb 用例数据 10 + janssonrpcc 3 + rtpproxy 3 + tm 1）。
- `src/modules/db_postgres/` 模块自身源码目录内**无测试源**、无 `check`/`ctest` 目标注册
  （模块内只有 `doc/`）。

### 2. 运行（唯一自包含入口，真实执行）

- `utils/kamctl/dbtextdb/dbtextdb_test.py` 是上游自带 unittest 入口（3 个用例：testParseQuery /
  testOpenTable / testExecute），仅依赖 Python 标准库，用例数据取自同目录 `tests/`。
- 已在 `conanfile.py` 的 `build()` 末尾真实执行：

```
Ran 3 tests in 0.049s
OK        # 3/3 通过，0 失败 0 错误
```

- 其余 14 个文件逐项不可执行原因见 `test_package/MANIFEST.yml` 的
  `upstream_tests[].not_executed_reason`（需同源码树构建的 kamailio 主程序 + 运行实例 /
  纯数据 / 需 root 的宿主 IPC 清理脚本）。

### 3. 回填

- `manifest.yaml` 的 `upstream_tests`（test_count=17 / executed_count=3 / passed=3 / failed=0）
  与 `test_package/MANIFEST.yml` 的逐条台账均已按实测回填。

## 五、验证记录（本机 conan create，2026-10-10）

```
$ conan create archives/k/kamailio-postgres/6.0.6 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
  -> build(): make cfg include_modules=db_postgres（LOCALBASE=<libpq> LIBPQ_BUILDER= PGCFG=）
              make modules modules=modules/db_postgres -j1
              → [M db_postgres.so] 构建成功，0 error
              → 上游测试：Ran 3 tests … OK（3/3）
  -> package(): lib/kamailio/modules/db_postgres.so + licenses/COPYING
  -> test_package:
     - check_db_postgres.py：ALL CHECKS PASSED（12 项：ELF64/ET_DYN/AArch64、NEEDED 含
       libpq.so.5、db_bind_api/db_postgres/kam_exports 标记、DF_1_NOW、无 RPATH/RUNPATH、
       NEEDED 全为纯文件名、licenses/COPYING）
     - test_db_postgres_e2e：dlopen → db_postgres_bind_api → 9 项回调绑定断言 →
       use_table 正例（表名真实写入连接句柄）+ 3 项负例 → init 联库段 SKIP（无 core 连接池/
       PostgreSQL 服务端）→ E2E OK（15 项断言全通过，1 项 SKIP）
  -> Full package reference:
     kamailio-postgres/6.0.6@ohpcd/stable#befb446f539c3c6077f1ff8ed4bd2553:76fd2f7f67dece130c9907f35828a3845ee631d4#4547001d864b9ab84b4f93bb2884c4cc
  -> 日志：reports/conan-create.log
```

- **鸿蒙特有端到端用例（test_db_postgres_e2e.c）**：以消费者身份走通 kamailio core 的
  loadmodule 路径（dlopen → `exports.cmds` 的 `db_bind_api` → 回调绑定 → use_table 真实调用）。
  由于 OHOS/musl 无惰性绑定（模块自身 BIND_NOW），必须随测试可执行文件编译
  `kamailio_core_stub.c`（最小 core 符号层，符号集逐项来自
  `llvm-nm -D --undefined-only db_postgres.so` 去除 libc/libpq 后的清单）并以
  `-Wl,--export-dynamic` 导出，dlopen 才能解析 core 符号。

## 六、已知限制

1. `db_postgres.so` 是 kamailio 的 core 插件，**真正连库需要运行中的 kamailio + 可用
   PostgreSQL 服务端**（core 连接池 + 服务端均不在本包可自动化范围）；e2e 用例覆盖
   dlopen→bind_api→回调绑定→use_table（含负例），联库段打印 SKIP 及原因。
2. 本包只交付模块 `.so`（不含 kamctl 的 postgres 配置脚本，理由见第二节）。
3. 与其它 kamailio 模块包相同：模块由 kamailio 运行时加载，不作为链接库供消费者链接。
