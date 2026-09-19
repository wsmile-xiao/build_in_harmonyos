# libicns 0.9.0 adaptation notes

## Scope

- Official source: https://github.com/kornelski/libicns — master declares
  `AC_INIT(libicns, 0.9.0)` via configure.ac; pinned commit
  `1137b6f67eed87fe7a31c7de5325686422bc4568` (official GitHub archive,
  no git tags on the repo; codeload/api confirmed master == 0.9.0).
- tarball SHA-256:
  `99922a929a975daea5fdcec616b3224114f73df551971b200bd928e73cf25f22`
  (verified: two independent codeload downloads byte-identical; tree
  diff against master = empty).
- License: library (`src/`) LGPL-2.1-or-later; bundled CLI tools
  (`icnsutils/`) GPL-2.0 — separate executables, declared together.
- Difference vs 0.8.1: source tarball ships **no** generated Autotools
  files (no configure/config.guess/config.sub/Makefile.in/m4), so the
  recipe bootstraps them in build() (aclocal → autoconf → autoheader →
  libtoolize → automake), following the abiword-plugin OHOS pattern that
  avoids the full autoreconf chain (HMDFS autoconf.m4f conflict).

## Dependency gate

- Hard dependency: libpng (`AC_CHECK_LIB(png, ...)` → AC_MSG_ERROR).
  `libpng/1.6.58` published on ohpcd registry, declared
  `transitive_headers=True` (libicns.pc carries `Requires: libpng`).
  Verified via `conan download --only-recipe` (RC=0).
- Optional dependency: jasper/openjpeg2 JP2 backends — only
  `AC_MSG_WARN` when absent; not declared, configure deterministically
  builds without 256x256/512x512 support.

## Build design

- Boostrap in build(): aclocal → `autoconf -o configure configure.ac`
  → autoheader (with config.h.in touch fallback) → libtoolize (copies
  ltmain.sh + m4/) → automake --add-missing --copy --force-missing.
  Generated files are 2023-08-22 config.guess/config.sub (modern
  LIBC-detecting scripts — different from 0.8.1's 2012-era scripts).
- OHOS adaptations applied in build() after bootstrap (contract-checked
  anchors; every generated file is re-created per build):
  1. config.guess: `*:HarmonyOS:*:*` case → MACHINE mapping →
     `GUESS=${MACHINE}-unknown-linux-ohos` (inserted before
     `aarch64:Linux:*:*`).
  2. config.sub: `linux-ohos*` added to the kernel-OS validation list
     (`linux-gnu* | linux-dietlibc* | ... | linux-ohos*`) and `ohos*`
     added to the OS accept-list tail (`... | zephyr* | ohos*)`).
  3. configure + config.guess: `umask 077` → `umask 022` (config.guess
     3 sites, configure 2 sites) — HMDFS temp dirs created with `umask
     077` end up not writable by the effective user (config.guess dies
     "can't create .../dummy.c: Permission denied").
  4. Every configure/make/check/install runs with
     SHELL/CONFIG_SHELL=/system/bin/sh and MKDIR_P=/system/bin/mkdir -p
     (HNP Bash getcwd failure inside HMDFS Conan build folders); TMPDIR
     bound to build-local .tmp; LD_LIBRARY_PATH prepended with every
     dependency libdir so configure conftest can dlopen libpng16.so.
- Shared library default (upstream `-version-info 3:0:2` preserved);
  installed libicns.pc rewritten to package-relative paths, obsolete
  libicns.la deleted.

## Tools (R38)

`bin_PROGRAMS = icns2png icontainer2icns png2icns icnsutil` — installed
under `bin/`, all four declared in software-level `commands.json`
(icnsutil is new in 0.9.0 vs 0.8.1). `icns2png --version` exits 1 by
upstream design (`CONVERSION_SHOWDOC`), CI L2 treats as non-blocking
observation matching the upstream CLI contract.

## Tests

### 上游测试三步法申报 (R51)

清点 (make -n check / 源码枚举):
- `TESTS` / `check_PROGRAMS` / `check_SCRIPTS` 声明: 0 处
  (Makefile.am / src/Makefile.am / icnsutils/Makefile.am / configure.ac)
- samples/ 仅 3 个数据文件 (test1.icns test2.rsrc test3.bin), 无断言代码
- 无 tests/ 目录、无 ctest/meson、无测试脚本
- icnsutils/*.c 的 `main()` 均为 CLI 工具本体, 非测试用例
- configure.ac 15 个 AC_RUN_IFELSE/AC_CHECK_* 为功能探测宏, 非测试用例

实测:
- `make -j1 check` RC=0 (Nothing to be done for 'check', 全部子目录)
- conan create 内 build() 同样执行 `make -j1 check` RC=0

结果: 上游独立测试用例 0 个。
- source_declared_total      = 0
- configured_executable_total = 0
- executed_passed_total       = 0
- failed                     = 0
- uninstantiated             = 0
- 双口径通过率: 0/0 (源码声明), 0/0 (当前配置可执行)

### test_package (消费者视角)

- test.c: 全链路公开 API 往返 — create family → 32×32 ARGB 合成 →
  icns_new_element_from_image → set/get element → decode + 像素对比 →
  icns_get_image_info_for_type/icns_type_str → export/import blob →
  write/read 真实临时文件往返 (26 CHECK + 6 fail 站点)。
- test_ohos_libicns.c (OHOS 专项, 独立计数): dlopen("libicns.so") 验证
  打补丁的 config.guess/sub 产出可加载共享对象 → TMPDIR 16×16 文件往返
  + stat 权限检查 (HMDFS umask 022 适配, 13 CHECK + 3 fail 站点)。
- 消费者测试计数: upstream 0/0, test_libicns 1/1, test_ohos_libicns 1/1
  (断言内部计数记入 MANIFEST.yml assertion_count, 非用例)。

## Current state

- `conan create` (G0-G4 + L2/L4/L5): PASS —
  `reports/conan-verify-report.md` + `reports/conan-create.log`
- test_package 消费者测试编译并运行: PASS (conan-create.log RUN 段)
- `make -j1 check`: 上游无测试套件 (0/0), RC=0
- `python3 -m py_compile` conanfile.py/test_package/conanfile.py: PASS
- 知识: DRAFT-E564 覆盖 2012-era config.guess 旧式脚本; 0.9.0 用的是
  现代 2023-08-22 脚本, HarmonyOS 支持缺失模式不同 (无 LIB C 探测分支
  命中), 且引入 HMDFS umask 077 临时目录不可写的新组合 — 见任务 #11
  的路径 B 草稿决定。

**编译结束**: 2026-09-18 (conan create + 消费者测试 PASS)
**最终状态**: built — pending commit/push/PR (本轮 task_id 内交付)
---

**编译结束**: 2026-09-18 23:15
**最终状态**: built
