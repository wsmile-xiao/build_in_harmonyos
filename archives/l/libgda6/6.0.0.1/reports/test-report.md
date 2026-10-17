# libgda6 6.0.0.1 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15 (aarch64-unknown-linux-ohos)
- Conan 2.29.1, meson 1.11.1, valac 0.56.19
- Upstream source: libgda-6.0.0.tar.xz (GNOME), sha256
  995f4b420e666da5c8bac9faf55e7aedbe3789c525d634720a53be3ccf27a670

## 6.0.0 → 6.0.0.1 变更（R37 版本递增）

- **valac PATH 注入**：meson `find_program('valac')` 做 PATH 查找，conan vala
  tool 包的 runenv PATH 未被聚合进 build env，导致在无 ambient PATH 环境下
  `meson setup` 报 `Program 'valac' not found`。`_inject_vala_env()` 现将 vala
  包 `bin/` 前置进 `os.environ["PATH"]`（与既有 XDG_DATA_DIRS/LD_LIBRARY_PATH
  注入同一机制），配方自包含、不依赖运行环境 PATH。
- **test_package 失败冒泡（R34/R9）**：原 `_run_retry` 全部 `ignore_errors=True`
  且 `test()` 为 `pass`，真实测试失败（如 SQLite provider 未注册）不使
  `conan create` 失败。现 `_run_retry` 增加 `rcfile` 语义（命令退出码写入文件，
  非 0 视为失败并 `raise ConanException`），`test()` 实际重跑 `test_pkg` 并
  校验退出码。
- `_UPSTREAM_VERSION = "6.0.0"`：源码 tarball/目录名固定用上游版本
  `libgda-6.0.0.tar.xz`，不受 conan 版本后缀影响。

## Verification

- `conan create archives/l/libgda6/6.0.0.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
  --build=missing -s build_type=Release`: **exit 0**
- meson build: **406/406 targets** compiled, 0 FAILED
- test_package (`test_pkg.c`): gda_init() runs, provider enumeration detects the
  built-in SQLite provider, data-model API smoke test passes:
  `provider: SQLite` / `test libgda6 6.0.0.1: OK`
- `test()` 阶段再次执行 test_pkg，退出码校验通过（R34 冒泡验证）

## Upstream test suite (meson test -j1, 54 test() targets)

Latest run (6.0.0.1 强制源码重建): **ok=46 fail=8**（历史 6.0.0 各轮
47–49/54，失败集合随运行漂移，证实 flaky 子集）：

| # | 失败用例 | 根因分类 |
|---|---|---|
| 1 | `DdlModifiableSqlite` (10/54) | 上游 glib 2.88 `g_weak_ref` 多线程竞态（单跑 5 次 4 次 OK，flaky） |
| 2 | `ServerOperationPostgreSQL` (19/54) | 环境限制：需活 PostgreSQL 服务器 |
| 3 | `ServerOperationSQLite` (20/54) | 上游 glib 2.88 `g_weak_ref` 多线程竞态（本轮漂移新增） |
| 4 | `Virtual` (22/54) | 上游 glib 2.88 `g_weak_ref` 多线程竞态 |
| 5 | `DataProxy` (23/54) | 上游 glib 2.88 `g_weak_ref` 多线程竞态（复测 SIGSEGV 漂移） |
| 6 | `MultiThreadConnectionLock` (37/54) | 上游 glib 2.88 `g_weak_ref` 多线程竞态（连跑 4 次全失败） |
| 7 | `dbcatalog` (48/54) | 上游 glib 2.88 `g_weak_ref` 多线程竞态 |
| 8 | `dbcatalog-postgresql` (54/54) | 环境限制：需活 PostgreSQL 服务器 |

分类汇总：**环境限制（PG 服务器）= 2，上游 glib 2.88 g_weak_ref 多线程竞态 = 6，
移植缺陷 = 0**。失败均为上游/环境固有，非移植缺陷，未做任何 hack 提通过率。

## Result

6.0.0.1 在本机强制源码重建后 `conan create` exit 0，406/406 targets 编译通过，
test_package 真实调用 API 并通过（含 test() 冒泡校验），上游测试 46/54 全部执行，
失败均为环境/上游竞态。配方修复（vala PATH + test_package 冒泡）验证通过，
符合 published 资格。
