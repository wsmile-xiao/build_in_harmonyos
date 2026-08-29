# DRAFT-astrometry.net-0.98-kv1 — vendored GSL config.guess 不识别 HarmonyOS

> 对应 KV：`knowledge/drafts/DRAFT-astrometry.net-0.98-gsl-config-guess.kv`
> 触发事件：astrometry.net 0.98 HarmonyOS PC 适配（R04–R14）

## 问题（error_signature）

vendored GSL（`gsl-an`）的 `config.guess` 2016-04-02 版本不包含 HarmonyOS/HongMeng Kernel
操作系统识别，configure 阶段报：

```text
config.guess: unable to guess system type
configure: error: cannot guess build type; you must specify one
```

## 根因（root_cause）

vendored GSL（`gsl-an`）的 `config.guess` 2016-04-02 版本不包含 HarmonyOS/HongMeng Kernel
操作系统识别，configure 阶段报 `unable to guess system type`。

## 方案（fix_approach）

1. **方案一（推荐）**：`requirements` 声明系统 GSL（如 `gsl/2.8`），设置
   `PKG_CONFIG_PATH` 使 `pkg-config --atleast-version gsl` 成功，Makefile 的
   `SYSTEM_GSL=yes` 会跳过 vendored gsl-an。
2. **方案二**：在 `gsl-an/Makefile` 的 configure 调用追加
   `--build=aarch64-unknown-linux`。
3. **附加**：`gsl-an/sys/infnan.c` 需同时定义 `HAVE_DECL_FINITE=1` 与
   `HAVE_DECL_ISNAN=1`（OHOS clang 提供 C99 `finite`/`isnan`）。

## 验证（verification）

- `make check` EXIT=0；G1/G2/G3 PASS；`finish` EXIT=0
- 编译日志确认 `-I<gsl package_folder>/include` 传入

## 适用边界（applicable_to）

所有在 OHOS 上编译含旧版 `config.guess`（2016）的 autotools 项目；含 vendored GSL 的任意项目。

## 元信息

| 字段 | 值 |
|------|-----|
| id | `DRAFT-astrometry.net-0.98-kv1` |
| trigger_tool | `configure`/`make`/`config.guess` |
| phase | `configuration` |
| severity | 2 |
| category | `toolchain`/`platform`/`autotools`/`gsl` |
| conan_package | `gsl/2.8` |
| platform | OHOS 6.0 arm64 (HongMeng Kernel) |
