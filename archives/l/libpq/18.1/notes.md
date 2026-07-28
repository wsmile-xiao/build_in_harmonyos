# libpq 18.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-28
- 编译器: clang/clang++（`/data/service/hnp/bin/clang`）
- 状态: built（鸿蒙 PC 真机原生 `conan create` 通过，test_package `dlopen libpq.so ok`）

## 为什么要 18.x（而非沿用 17.x）
`psycopg[c]`（psycopg 的 C 加速）的 `psycopg-c 3.3.x` 是按 **libpq 18** 编译的，运行期 `dlopen` libpq
时会解析 **`PQfullProtocolVersion`**（PostgreSQL 18 新增的函数）。用 libpq 17.x 会报
`PQfullProtocolVersion: symbol not found`，psycopg 退回 “no pq wrapper available”。因此在鸿蒙上用
psycopg（langgraph 的 Postgres checkpointer 等）必须提供 **libpq 18.x**。

## 编译步骤

1. 打 3 个补丁（`patches/`）：
   - `0001-config.guess-harmonyos.patch`：`config/config.guess` 识别 HarmonyOS → 输出 `aarch64-unknown-linux-ohos`
   - `0002-config.sub-ohos.patch`：`config/config.sub` 补 `ohos-linux)` 映射 + accept 列表 `ohos*`
     （PG18 的 config.sub 已自带 `linux-ohos*-` 内核分支，故本版比 17.2 少一个 hunk）
   - `0003-configure-tmpdir.patch`：`configure` 的临时目录改用 `${TMPDIR:-$HOME/tmp}` + `umask 000`
     （media 文件系统上 `umask 077` 建的目录组不可写 → config.status 写 `subs*.awk` Permission denied）

2. configure（补丁后 config.guess 认得 HarmonyOS，无需 `--build/--host`）：
   ```bash
   ./configure --without-readline --without-zlib --without-icu \
               --without-openssl --without-libxml --without-gssapi
   ```

3. 仅编客户端库 libpq：
   ```bash
   make -C src/interfaces/libpq        # 自动 submake src/port + src/common
   make -C src/interfaces/libpq install
   ```

4. 补装公共头（关键）：`libpq-fe.h #include "postgres_ext.h"`，而 `postgres_ext.h` / `pg_config_ext.h`
   在 `src/include/`、不随 `src/interfaces/libpq install` 安装 → 需手动一并拷进 `include/`，否则消费方
   （psycopg-c 等）编译报 `postgres_ext.h file not found`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess `cannot guess build type` | 脚本不含 HarmonyOS 检测 | 0001 补丁识别 HarmonyOS |
| 2 | `Invalid configuration ...linux-ohos` | config.sub accept 列表缺 ohos* | 0002 补丁补 ohos*（PG18 已有 linux-ohos 内核分支） |
| 3 | config.status 临时目录 `Permission denied` | media fs 上 umask 077 剥组写位 | 0003 补丁改 umask 000 + `$HOME/tmp` |
| 4 | 消费方编译 `postgres_ext.h file not found` | 该头在 src/include/、libpq 子目录 install 不装 | 手动补装 postgres_ext.h + pg_config_ext.h |
| 5 | psycopg `PQfullProtocolVersion: symbol not found` | psycopg-c 3.3 按 libpq 18 编，17.x 无此符号 | 使用 libpq 18.x |

## 源码修改
均通过 `patches/` 应用，不改上游源码树以外内容：
- `config/config.guess`、`config/config.sub`、`configure`（见上 3 个补丁）
