# lcrq

`lcrq` 是 Librecast Project 的 RaptorQ (RFC6330) 前向纠错库：提供系统化 RaptorQ
编码/解码（`rq_init`/`rq_encode`/`rq_decode`/`rq_free`）、OTI 导出与反解、以及内部
`q` 任务队列。aarch64 走 NEON 实现。上游官方仓库
[Codeberg librecast/lcrq](https://codeberg.org/librecast/lcrq)。

## Homepage
https://librecast.net/lcrq.html

## License
GPL-2.0-only OR GPL-3.0-only

## Build System
Autotools (configure + make)

## Dependencies
- None (pure C, libc only)

## OHOS Adaptation
- config.guess 2022-05-25 cannot recognize HarmonyOS — patched via `patch-autotools-ohos.pl`
- config.sub additionally required `linux-ohos*` in the kernel-os validation table
- Upstream `src/Makefile.in` is hand-written, in-source only (no VPATH) — conan recipe uses `basic_layout(self, build_folder=".")`
- Upstream tarball contains dangling symlinks `test/all/*.test` (resolved at build time) — incompatible with shutil.copytree on HMDFS
- Shared library only (`all: $(SOFILE)`); no static build target upstream
- soname 别名 `ln -sf` → `cp -f`（真机文件系统符号链接受限）
- configure 临时目录 umask 077→002（HMDFS 700 目录不可读）

## Versions
- 0.3.1 — built 2026-09-19 (upstream `make test` 19 run / 18 OK / 0 FAIL / 1 SKIP; test_package encode/decode roundtrip OK)
- 0.4.1 — built 2026-09-22 (upstream `make test` 20 run / 20 OK / 0 FAIL; test_package rq_init/rq_oti/rq_oti_F/rq_oti_T/rq_F/rq_T/rq_Z/rq_N/rq_K 9 项断言编译链接通过)

## Testing

上游 `make test` 覆盖 RaptorQ 编解码往返、参数域、符号/块映射与 q 队列（20 用例，
断言 ≈146）。Conan 消费者测试（`test_package/`）实质调用 `rq_init`/`rq_oti`/
`rq_oti_F`/`rq_oti_T`/`rq_F`/`rq_T`/`rq_Z`/`rq_N`/`rq_K`，校验 OTI F/T 反解往返一致。
