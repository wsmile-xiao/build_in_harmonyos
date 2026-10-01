# scdoc 1.11.3

The Makefile builds a `scdoc` binary and then executes it to generate its own
man pages. During OHOS cross builds the recipe compiles a build-machine
`scdoc-host` helper for those generation steps, while the packaged `bin/scdoc`
remains the target aarch64 binary. No external Conan requirements are needed.

## Findings and fixes

1. Windows w64devkit `make check` resolved `find` to the system command and
   stopped with `FIND: Parameter format not correct`; the same upstream suite
   passed 44/44 when run from WSL with GNU `find` and `date`.
2. W3 r003 returned target RC 0 but failed the frozen marker comparison because
   the produced marker was `.TH "scdoc" "1"`; r003 remains immutable. The
   create-new r004 run used the native OHOS self-sign signer and passed the
   exact marker, target execution, and postrelease checks.
3. The recipe now declares `export_sources()` and
   `apply_conandata_patches()` even though this version has no patches. The
   test package includes a real consumer script and `MANIFEST.yml` so CI L0c-L0e
   can verify the test surface.
4. Platform CI #39446 showed that an OHOS worker can provide only the target
   compiler and no build-machine `gcc`/`cc`. The recipe now treats the host
   generator as optional and copies checked-in man pages when no host compiler
   is available; it still regenerates them when a host compiler exists.
   The source-bound pages are `man/scdoc.1`
   (`545659b77908573a04b4134e864f24d5db608c1ee942d7362531f7d9227ab04c`)
   and `man/scdoc.5`
   (`f4f00f45283e20a6ec8bcec4a58be8e04be7310cecd9551377c665853e531e91`).
5. After the host fallback was fixed, CI #39466 reached target linking but
   `lld` could not load `libxml2.so.16`. Target compiler commands now prepend
   the compiler's `llvm/bin` and `llvm/lib` directories to `LD_LIBRARY_PATH` on
   POSIX workers, without changing Windows command construction.

## Verification

- Conan create: PASS; RREV `dc3700ceba8050e86ec2bfea6a383063`, package ID
  `eda5abb401cbed7c3f6f2ad04bfecec451641886`, PREV
  `9e840d7830f17e5624fc30bc31372bf1`.
- Upstream suite: 44/44 PASS; raw log is
  `reports/upstream-make-check-wsl.log` with SHA-256
  `e1e42cde564b226e271e63afafa8d4d271e6fbc6ce52f2d278e4a5f56c3fda93`.
- Target W3 r004: one launch, RC 0, stderr 0, output 338 bytes, native
  signer, exact marker, postrelease PASS.
- Platform CI #39446: failed in `_build_host_generator()` because the worker
  had no build-machine compiler; this is the failure fixed by the prebuilt man
  page fallback.
- Platform CI #39466: target `lld` failed to load `libxml2.so.16`; the runtime
  path binding is the targeted fix for this worker toolchain boundary.

---

**编译结束**: 2026-09-04 16:20
**最终状态**: built
