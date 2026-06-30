# wal2json 2.6 — OHOS 适配版本

wal2json 2.6 是 PostgreSQL 逻辑解码输出插件，将 WAL 变更集转换为 JSON 格式输出。

## 本版本说明

- **目标平台**: OpenHarmony / HarmonyOS (aarch64)
- **构建系统**: PGXS → 自定义编译（因缺少 PostgreSQL 安装）
- **产物**: `lib/wal2json.so` (ELF shared object, 64-bit LSB arm64)
- **签名**: 含 `.note.ohos.ident` 和 `.codesign` ELF 签名段
- **RUNPATH**: `$ORIGIN:$ORIGIN/external`
- **依赖**: 仅 libc.so

## OHOS 适配要点

1. **构建依赖**: PostgreSQL 开发头文件 + pg_config
   - cmd-pkgs 无 PostgreSQL 预编译包
   - 从 PostgreSQL 16.4 源码获取头文件
   - 创建最小 pg_config wrapper 脚本指向源码树

2. **E097 修复**: PostgreSQL config.status 在 HMDFS 上无法创建临时文件
   - 使用 Python 脚本从 config.status 提取替换数据，手动处理 .in 模板

3. **类型定义**: aarch64 上 PG_INT64_TYPE = `long int` (long=8字节)

## 编译命令

```bash
clang -Wall -Wmissing-prototypes -Wpointer-arith \
  -Wdeclaration-after-statement -Wformat-security \
  -fno-strict-aliasing -fwrapv -Wno-unused-command-line-argument \
  -fPIC -O2 \
  -I. -I$PGSRC/src/include -I$PREFIX/include \
  -D_GNU_SOURCE -DHAVE_CONFIG_H \
  -c wal2json.c -o wal2json.o

clang -shared -fPIC -o wal2json.so wal2json.o -lm
```

## 部署方式

1. 解压 `wal2json-2.6-ohos-aarch64.tar.gz`
2. 复制 `lib/wal2json.so` 到 PostgreSQL 的 `pkglibdir`（通常 `$PG_PREFIX/lib/`）
3. 配置 PostgreSQL: `wal_level = logical`, `max_replication_slots ≥ 1`
4. 创建逻辑复制槽:
   ```sql
   SELECT pg_create_logical_replication_slot('wal2json_slot', 'wal2json');
   ```

## 回归测试

wal2json 回归测试需要 PostgreSQL 服务器运行环境，交叉编译环境无法执行。
详细验证结果见 [test-report.md](reports/test-report.md)。

## 许可证

BSD-3-Clause (Copyright (c) 2013-2024, Euler Taveira de Oliveira)