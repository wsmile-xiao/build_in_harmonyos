# libkibi 0.1.1 adaptation notes

## Scope

Path A (basic adaptation). libkibi is a tiny C library for formatting byte
sizes with SI/binary prefixes (ISC license, Benjamin Drung). No third-party
Conan dependencies. Autotools build (`configure` + `make`), one libtool
library (`libkibi.la` -> `libkibi.a`/`.so`, public header `kibi.h`).

## Source

- URL: `https://launchpad.net/libkibi/trunk/0.1.1/+download/libkibi-0.1.1.tar.xz`
- SHA-256: `3932f20a5f328f00284ed7c2289c51fa6671167057c8da845d26dee0cf448271`
- Size: 228032 bytes, MD5 `01447a50669eaea42ec9628c25f950bd` (matches Debian orig)
- License: ISC (`COPYING`)
- Layout: `kibi/` (lib), `test/` (suite), `doc/`, `build-aux/`, `m4/`

## Upstream tests

- `test/Makefile.am`: `TESTS = test-base10 test-base2 test-historic`, `check_PROGRAMS = test`
- 3 shell wrappers export `BYTEPREFIX=<mode>` and run `./test <mode>`; the C
  binary (`test/test.c`, ~727 lines, 16 testcase arrays) checks divide/multiply,
  format_size/detailed/memory/transfer/si/value, get_unit_for_size/transfer_rate,
  and the `kibi_n_*` bounded-buffer variants under each prefix mode.
- `make check` builds the lib + test binary and runs all 3 scripts.
  discovered = 3 (scripts); executed/passed come from the real `make check` run
  in `build()` and are emitted as `HMBS_UPSTREAM_TEST_RESULT`.

## OHOS adaptations

1. `--host/--build` override on OHOS: 2013 `build-aux/config.sub` knows
   `aarch64` CPUs but predates `linux-ohos`/`harmonyos`, so the Conan OHOS
   triplet (`aarch64-linux-ohos`) is rejected as invalid. The recipe passes
   explicit `--host=aarch64-linux-gnu --build=aarch64-linux-gnu` (x86_64
   likewise) on OHOS only; the real target is still set by the profile compiler
   (`/data/service/hnp/bin/clang`). Precedent: lame 3.100. No config.* patches.
2. `umask 077` -> `umask 022` normalization in `configure` (config.status tmpdir
   creation hits HarmonyOS SELinux/HMDFS restrictions). Same class as ldns 1.9.0.
3. `make -j1` (OHOS platform constraint), `--with-default-prefix=base10`
   (matches upstream default), `rm *.la` after install.
4. `build()` runs `make check` and emits `HMBS_UPSTREAM_TEST_RESULT`
   (discovered=3); the JSON is persisted to `res/hmbs_upstream.json` so
   test_package can re-emit it on cache hits. test_package emits
   `HMBS_TEST_PACKAGE_RESULT` after running the installed-package consumer.

## Test_package (consumer)

- `test_package.c` links the installed `kibi` lib and exercises output + input
  APIs: `kibi_format_size`, `kibi_format_memory_size`,
  `kibi_format_transfer_rate`, `kibi_format_value`, `kibi_divide_size`,
  `kibi_multiply_size`, `kibi_get_unit_for_size`,
  `kibi_get_unit_for_transfer_rate`, plus one `kibi_n_format_size` bounded call.
- Each stage prints one `CHECK n OK` line (9 stages); `test()` requires exit 0
  AND all 9 lines, so an empty stub cannot fake green.

## Validation

- Local (Windows): recipe files written; no local `conan create` per project
  policy (validation happens on the HarmonyOS PC via HMBS preflight).
- Awaiting HMBS preflight: `make check` (3/3) + consumer (1/1). Numbers in the
  PR body will be filled from that evidence only.

## Risks

- Old libtool `ltmain.sh` shared linking on OHOS is unproven here; default is
  static (`shared=False`). Shared remains offered and will be validated if CI
  exercises it.

## 2026-09-18 preflight fix (kibi.h VPATH)

- `make check` failed: `build/test` compile used relative `-I../kibi`, broken
  for Conan out-of-tree builds (`fatal error: 'kibi.h' file not found`).
- Fix: `generate()` appends `CPPFLAGS=-I<source>/kibi` to configure args;
  `build()` re-patches the generated `test/Makefile` with the absolute include
  as fallback. No tests skipped.

## 2026-09-18 preflight fix (install phase)

- `make check` now passes 3/3, but `package()` failed: the platform `install`
  shim exited 0 yet `.../p//lib/libkibi.a` never landed, so libtool's
  follow-up `chmod 644` died with "No such file or directory".
- Fix: `package()` reuses the writable TMPDIR root (readonly_tmp also covers
  install staging), then verifies the install set; when `make install`
  under-delivers, the exact same files (`kibi.h` + `kibi/.libs/libkibi.*`
  minus `*.la`, symlinks preserved) are staged manually. If the set is still
  incomplete the original install error is re-raised, and test_package
  link-checks the staged artifacts.

## 2026-09-18 preflight fix (kibi.h size_t)

- `make check` 3/3 通过、安装与 test_package 工具链修复后，`test_package`
  编译失败：`kibi.h:189: error: unknown type name 'size_t'`（6 处原型）。
  上游公头直接用 `size_t` 却不含 `<stddef.h>`；上游自带测试因先含其他
  头而隐蔽，消费者首行 `#include <kibi.h>` 即暴露。
- Fix：`build()` 对源码 `kibi/kibi.h` 做一次性规范化（无 `stddef.h`
  才在保护宏/注释后插入 `#include <stddef.h>`，`package()` 随源拷贝
  自动带出修复）；`test_package.c` 同步把标准头前置、`kibi.h` 后置，
  双层兜底，不改测试口径不断言跳过。

## 2026-09-18 preflight fix (test_package toolchain)

- 主包 `make check` 3/3 通过、安装兜底生效后，`test_package` 的 CMake
  configure 失败：`CMAKE_SYSTEM_NAME=HarmonyOS` 无 Platform 文件，且
  profile 的 `CMAKE_C_COMPILER=/data/service/hnp/bin/clang` 在沙箱内不可用。
- Fix（xmlsec/1.3.12 同机先例）：`CMAKE_SYSTEM_NAME` 强制 `Linux` 别名；
  conf 编译器经 `--version` 存活检查，不可用则回退 HMBS_CC/CC/PATH 的
  clang；`build()` 复用可写 TMPDIR。另收紧主包兜底，只搬运可链接二进制
  （`.a`/`.so*`），不再搬运 libtool 的 `.lai` 中间文件。
