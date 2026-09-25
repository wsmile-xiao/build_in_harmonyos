# DRAFT-ohos-siril-gapplication-callback-exit-deadlock：OHOS glib 上 GApplication 选项回调内 exit() 死锁

> Contributor: SnowTT | Status: Draft | Updated: 2026-09-05
> Source: siril 1.2.3 适配（conan-verify test_package/L2 smoke 修复链）

## 背景

siril-cli（GTK3 应用的命令行前端）在 conan create 的 test_package 中执行
`--version` 时永久挂死（futex 阻塞，S 状态，~30MB RSS = GTK 已加载）。同一现象覆盖
`--version/-v/--copyright/-c/--format/-f` 全部用户自定义 GOptionEntry；仅 glib 内建
`--help` 能正常退出。加 LD_LIBRARY_PATH、关闭 stdin、清空 XDG 目录均无法规避。

## 根因

OHOS 的 glib 上，`g_application_run()` 在 GOptionEntry ARG_CALLBACK 内调用 `exit()`
会死锁：选项解析回调仍持有 glib 内部锁（GApplication 初始化/主循环锁），exit() 的
atexit/清理路径反向等待同一把锁 → futex 死锁。上游该写法在 Linux glibc 环境正常，
OHOS（musl + 裁剪 glib）环境必现。

## 修复

patch 0007（src/main-cli.c）：main() 一进入就调用新增的
`_cli_handle_early_print_options()`，对 `--version/-v`、`--copyright/-c`、
`--format/-f` 做手工识别（printf + return），完全不进入 GApplication；输出格式与
原回调保持一致。行为等价、无功能损失。

## 相关既有条目差异化定位

| 既有条目 | 差异点 |
|---------|--------|
| 无（查重：knowledge/index.tsv + graph/*.kv + drafts/*.kv 中 siril/GApplication/GOptionEntry 层面命中 0 条） | 新增问题层条目 |

## 验证

补丁后 `siril-cli --version` 输出 `siril 1.2.3` rc=0；conan create test_package 通过，
conan-verify 全绿。
