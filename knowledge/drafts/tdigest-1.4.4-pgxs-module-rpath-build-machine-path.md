# PGXS 服务端模块产物不应带构建机 rpath（`make rpath=`）

> 草稿（DRAFT）。与同目录 `tdigest-1.4.4-pgxs-module-rpath-build-machine-path.kv` 成对。

## 适用场景

用 **PGXS** 构建 PostgreSQL 扩展（`MODULE_big = <name>` / `MODULES = <name>` 形式的服务端
共享模块），且 `pg_config` 来自 conan `postgresql` 包（而不是系统安装）。

## 现象

```bash
$ readelf -d tdigest.so | grep -E "NEEDED|RUNPATH"
 0x000000000000001d (RUNPATH)  Library runpath: [/storage/<user>/.conan2/p/postgfee07d5886c8f/p/lib]
 0x0000000000000001 (NEEDED)   Shared library: [libc.so]
```

产物的 RUNPATH 指向**构建机的 conan 缓存绝对路径**。

## 根因

PG 的 `src/Makefile.global`（随 PGXS 一起提供）里：

```make
# Set up rpath if enabled.  By default it will point to our libdir,
rpathdir = $(libdir)
ifeq ($(enable_rpath), yes)
LDFLAGS += $(rpath)
endif
```

`libdir` 由 `pg_config --libdir` 提供 → 指到 conan 缓存里的包目录，于是链接行带上
`-Wl,-rpath,'<conan pkg>/lib'`。

**对服务端扩展模块来说这个 rpath 没有意义**：模块由 `postgres` 进程 `dlopen`，
所有 PostgreSQL 符号（`pg_detoast_datum`、`DirectFunctionCall*` …）都从该进程解析，
`DT_NEEDED` 只需要 libc。留着它反而把构建机路径固化进产物：破坏可复现性、
让 L5 产物基线随机器/缓存路径漂移。

## 推荐方案

给 make 传空的 `rpath=`，覆盖 PGXS 的 `-Wl,-rpath,'$(rpathdir)'`：

```bash
make PG_CONFIG="<conan postgresql>/bin/pg_config" rpath= -j1
readelf -d tdigest.so | grep -E "NEEDED|RUNPATH"
#  0x0000000000000001 (NEEDED)  Shared library: [libc.so]      ← 无 RUNPATH 行
```

这是链接标志层面的调整：不改上游源码、不需要补丁、不影响功能。

## 反例（禁止）

| 写法 | 结果 |
|---|---|
| `make rpathdir=` | 展开成 `-Wl,-rpath,'',--enable-new-dtags`，产物留下畸形条目 `RUNPATH: [--enable-new-dtags]` |
| 构建后 `patchelf --remove-rpath` | OHOS 产物需签名；后处理可能破坏签名/一致性，不如源头不写 |

## 证据（tdigest 1.4.4 @ OHOS PC aarch64）

| 状态 | 链接行 | `readelf -d` |
|---|---|---|
| 默认 | `... -L<pkg>/lib -Wl,--as-needed -Wl,-rpath,'<pkg>/lib',--enable-new-dtags` | `RUNPATH: [.../0.2/p/postgfee07d5886c8f/p/lib]` + `NEEDED: libc.so` |
| `rpath=` | `... -L<pkg>/lib -Wl,--as-needed` | 仅 `NEEDED: libc.so` |

去掉 rpath 后重新 `make install` 并无回归：上游回归套件 `pg_regress` **10/10 通过**，
产物 sha256 `8566e61c373ba0a9914a6239de78e2c623c1b68205da1534ff7bc0a49da52b7f`
（连续多次构建一致 → 可复现）。

## 关联

- 同批草稿：`tdigest-1.4.4-pg-regress-runpath-libpq-not-found`（测试侧同类 RUNPATH 陷阱）
- 规则：R26（系统同名库隔离）、产物可复现性/L5 基线
