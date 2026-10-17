# libpq

PostgreSQL客户端库，提供连接PostgreSQL数据库的C语言API。

## 软件简介

libpq是PostgreSQL的前端库，包含：
- 数据库连接API（PQconnectdb、PQsetdbLogin等）
- 查询执行API（PQexec、PQprepare等）
- 结果处理API（PQresultStatus、PQgetvalue等）
- 异步连接和查询支持
- SSL/TLS加密连接支持

## 安装指南

使用预编译包安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libpq 16
```

## 版本信息

### 18.6.1 (推荐版本，Conan)

**编译状态**：built ✅（真机 772 原生 `conan create`，test_package 16/16）
**编译日期**：2026-09-22
**Conan ref**：`libpq/18.6.1`

18.6 的打包修订：同一份 `postgresql-18.6.tar.gz`，`libpq.so.5.18` / `libpq.a` 与 `libpq/18.6` 逐字节相同，新增：
- `bin/pg_config` —— psycopg2 / psycopg-c(psycopg-binary) / asterisk 等在构建期先跑 `pg_config --includedir/--libdir` 定位 libpq，18.6 缺它就停在 `pg_config executable not found`
- 客户端头闭包（Debian libpq-dev 同集合）：`pg_config.h`、`pg_config_os.h`、`pg_config_manual.h`、`libpq/libpq-fs.h` + `postgresql/internal/` 下 5 个头；psycopg2 的 `#include <pg_config.h>` / `<libpq/libpq-fs.h>` 与 psycopg_c 的 `#include "pg_config.h"` 在 18.6 下都找不到

真机 772 端到端：psycopg2 2.9.12、psycopg-c 3.3.6 均从 sdist 编出 `ohos_aarch64` wheel 并 import 成功。

```bash
conan install --requires=libpq/18.6.1 -r ohpcd -pr:h ohos-aarch64 -pr:b ohos-aarch64 \
  --deployer=usr_local --deployer-folder=$HOME/usr/local
PATH=$HOME/usr/local/bin:$PATH pip wheel psycopg2   # pg_config 在 PATH 上即可
```

### 18.6 (Conan)

**编译状态**：built ✅　**编译日期**：2026-09-05　**Conan ref**：`libpq/18.6`
只含 `libpq.so` / `libpq.a` + libpq 子目录自装的头；已有 10 个下游 recipe 依赖，保持不动。

### 16 (cmd-pkgs 预编译包)

**编译状态**：published ✅
**编译日期**：2026-05-27
**质量门禁**：G0-G4全部通过

**产物详情**：
- libpq.so.5.16 (动态库，321KB)
- libpq.a (静态库，243KB)
- 头文件、pkgconfig文件

**关键技术**：
- VPATH构建避免HMDFS权限问题
- sed修改configure umask设置
- 禁用ICU依赖

## 编译详情

详见 `16/notes.md`。

## 许可证

PostgreSQL许可证（类似BSD/MIT）。