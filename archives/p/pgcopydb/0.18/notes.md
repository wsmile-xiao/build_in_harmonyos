# pgcopydb 0.18 适配笔记

## 编译环境
- 构建系统: 上游手写 Makefile（`make bin`），全部路径由 `pg_config` 推导
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4（OHOS PC 原生，aarch64）
- 依赖: `postgresql/18.3`（pg_config + 服务端头文件 + libpq.so.5 + libpgcommon/libpgport + pg_dump/pg_restore）、`gc/8.2.12`（Boehm GC，静态 libgc.a）
- 状态: built

## 编译步骤

```bash
conan create archives/p/pgcopydb/0.18 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

配方在 `build()` 中：

1. `apply_conandata_patches()` 应用 `patches/0001-ohos-platform-adaptation.patch`
2. 写入 `GIT-VERSION-FILE` / `version`（内容为 `0.18`）——上游 Makefile 的
   `GIT-VERSION-FILE` 规则会调用 `GIT-VERSION-GEN`（`#!/bin/sh`），预置该文件
   既固定版本号又免去对 POSIX shell 的依赖
3. 执行
   ```bash
   make bin -j1 \
     PG_CONFIG=<postgresql/18.3>/bin/pg_config \
     CC=<clang from tools.build:compiler_executables> \
     CFLAGS="-DHAVE_BROKEN_SYSV_SEM -DHAVE_BROKEN_SYSV_MSG -I<gc>/include" \
     LDFLAGS="-L<pg>/lib -Wl,-rpath,<pg>/lib -L<gc>/lib -Wl,-rpath,<gc>/lib" \
     LIBS="-lpq -lpgcommon -lpgport -lgc -lm"
   ```
4. `package()` 把 `src/bin/pgcopydb/pgcopydb` 装到 `bin/`（上游 `make install`
   使用 `install -d/-m`，OHOS 无该命令，故配方自行拷贝）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `pgcopydb --version` 直接 `Bad system call (core dumped)`（rc=159/SIGSYS） | OHOS 沙箱拒绝 System V IPC 系统调用：`semget`(190)/`msgget`(186)/`shmget`(194) 全部 SIGSYS；`main()` 一进来就 `semaphore_init()` → `semget` | `lock_utils.c/.h` 在能力宏下改用 POSIX 命名信号量（`sem_open/sem_wait/sem_post`） |
| 2 | 消息队列同样不可用（`pgcopydb clone` 会因为 vacuum/index 队列崩） | `msgget/msgsnd/msgrcv/msgctl` 同属 SysV IPC | `queue_utils.c` 在能力宏下改用 `MAP_SHARED|MAP_ANONYMOUS` 环形缓冲 + 进程共享 POSIX 信号量 |
| 3 | `pgcopydb clone --source ...` 报 `unrecognized option: source`，子命令分发整体失效 | musl 的 `getopt_long()` **不认** `POSIXLY_CORRECT`（glibc 认），仍对参数做置换，于是根命令把子命令的选项当成自己的未知选项 | `cli_root.c` 根 optstring 加 `+` 前缀（= "遇到第一个非选项就停止"，glibc 下语义与 `POSIXLY_CORRECT` 完全一致） |
| 4 | `-lpgcommon` 静态库缺 `pg_encoding_to_char` | `libpgcommon.a`（非 shlib）里是 `pg_encoding_to_char_private`；补 `libpgcommon_shlib.a` 又要求 `pfree/pstrdup` 等服务端符号 | 放弃静态 libpq：改用共享 `libpq.so.5`（本身只 NEEDED `libc.so`） |
| 5 | 二进制找不到 `libpq.so.5` | conan 包装的 `libpq.so` 带 SONAME `libpq.so.5`，但默认无 RUNPATH | 链接期加 `-Wl,-rpath,<postgresql>/lib`（`<gc>/lib` 同理） |
| 6 | 上游 `LIBS += -lncurses` 无法满足 | 全树唯一命中都在 vendored `sqlite3.c` 内部宏里，无任何 ncurses 符号被引用 | 配方直接给完整 `LIBS`，去掉 `-lncurses`（不引入无用运行时依赖） |

## 源码修改

唯一补丁 `patches/0001-ohos-platform-adaptation.patch`（4 个文件，925 行 diff）：

| 文件 | 改动 |
|------|------|
| `src/bin/pgcopydb/lock_utils.h` | 结构体新增 POSIX 句柄/重入归属字段（能力宏内） |
| `src/bin/pgcopydb/lock_utils.c` | 能力宏下用 POSIX 命名信号量实现 `semaphore_create/create_set/open/unlink/cleanup/lock/unlock`；原 SysV 实现整段保留在 `#else` |
| `src/bin/pgcopydb/queue_utils.c` | 能力宏下用匿名 `MAP_SHARED` 环形缓冲 + 进程共享信号量实现 `queue_create/unlink/send/receive/stats`；原 SysV 实现保留在 `#else` |
| `src/bin/pgcopydb/cli_root.c` | 根命令 optstring 加 `+` 前缀 |

**R8 合规**：补丁内不出现任何平台宏（`__OHOS__` 等），守卫全部是语义能力宏
`HAVE_BROKEN_SYSV_SEM` / `HAVE_BROKEN_SYSV_MSG`，**只由配方在 `settings.os == "OHOS"` 时注入**；
非 OHOS 平台这些分支整体不参与编译，与原实现逐字节等价（`#else` 分支原文未动）。

补丁生成方式：tar 解压的 `.orig` 基准树 vs `.work` 工作树，逐文件
`diff -u --label a/<f> --label b/<f>`；黄金验证 = `git apply --check` 全过 +
`patch_ng.apply(strip=0)` 应用后与 `.work` 树 `diff` 为空。

## 依赖版本

- `postgresql/18.3`（ohpcd 已发布制品，`conan download` 实测可拉取）
- `gc/8.2.12`（ohpcd 已发布制品，`shared=False` → `libgc.a`）

## 验证结果

```bash
# 本地端到端（本机 OHOS PC，两个真实 PG 18.3 实例，TCP loopback）
pgcopydb ping   --source ... --target ...
pgcopydb clone  --source ... --target ... --dir ...
pgcopydb compare schema/data --source ... --target ...
```

- `pgcopydb clone` rc=0：2 表 / 4 索引 / 序列 / schema 全部复制，目标行数与源一致
- `pgcopydb compare data` rc=0：源/目标逐表校验和完全一致
- `pgcopydb compare schema` rc=0
- 二进制 `DT_NEEDED` 仅 `libpq.so.5` + `libc.so`，带 `.codesign` 段
- `test_package/pgcopydb_test.py`：12/12 断言通过

**上游 `tests/unit` 真跑（见 `reports/upstream-tests.md`）**：15 例中
**12 例真实执行且通过**（9 个 `sql/*.sql` + 3 个 `script/*.sh`，逐例与上游
`expected/*.out` diff 一致），3 例阻塞（2 例需 ICU collation、1 例需
`pg_stat_statements`）；`copydb.sh` 尾部 issue-894 内联回归（`--use-copy-binary`
的 tsvector 回退）亦真跑通过。连续两轮结果一致。

## 已知限制

1. **25 个集成套件不可执行**：`tests/<name>/` 全部由 `docker compose` 驱动
   （`test` 服务镜像为上游 CI 自建的 `pagila`/`multi`/`pgcopydb`/`cdc-*`/`follow-*`，
   服务端另需 `wal2json`/`pgoutput`/`postgres:9.6`/`timescaledb`/`citus` 等镜像与
   `ssl=on`、`wal_level=logical`），HarmonyOS PC 无容器运行时，且这些镜像与
   逻辑解码插件无法在本机复现。`tests/unit` 与 issue-894 内联回归已真跑覆盖同一批
   代码路径（见 `reports/upstream-tests.md`）。
2. **CDC（`follow`/`stream`）未做真机链路验证**：其 IPC 已由本次适配迁移到
   POSIX 原语，但跨实例逻辑复制需要 `wal_level=logical` 的双实例长跑场景。
3. 产物通过 `-Wl,-rpath` 指向 conan 依赖库目录（`libpq.so.5` 为共享依赖）；
   `conanrun` 环境同样可用。
