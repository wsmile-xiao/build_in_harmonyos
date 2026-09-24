# libdvbv5 1.32.0 adaptation notes

## Environment

- Upstream project: v4l-utils (subtree `lib/libdvbv5`)
- Build system: Meson
- Date: 2026-09-22
- Status: built on OHOS (aarch64), `conan create` exit 0

## Dependency pre-check (W0)

`libudev` is a hard dependency. Verified consumable before starting:

```bash
conan download "eudev/3.2.14" -r=ohpcd --only-recipe     # exit 0
conan install --requires=eudev/3.2.14 -r=ohpcd --build=never \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# -> eudev/3.2.14:b2d2bdcc... Package installed
```

The installed package provides `include/libudev.h`, `lib/libudev.so.1.6.3`
and `lib/pkgconfig/libudev.pc`, so `PkgConfigDeps` can satisfy upstream's
`dependency('libudev')`.

## Language pre-flight (R47)

```
$ ohc-run.py lang-preflight libdvbv5 1.32.0 --src=<work>
task=cpp, detected=cpp — 继续适配主流程
```

## Upstream test inventory (R51)

```
$ meson test -C build --list
No tests defined.
$ grep -rn "^\s*test(" --include="meson.build" . | wc -l
0
```

Upstream registers **zero** tests. The only non-device libdvbv5 consumer is
`utils/dvb/dvb-format-convert`; it needs `argp`, which OHOS lacks, so it
cannot be built here. Its libdvbv5 code path was executed equivalently:

```
$ ./test_libdvbv5        # roundtrip fixture, 3 DVB-T channels
parsed_entries=3
write_ok
roundtrip_ok
exit=0
```

See `reports/upstream-tests.md` for the full inventory and per-entry reasons.

## Patches

Four patches, all portability-only and all generated with
`refresh-patch --auto` (no hand-edited diffs):

1. `0004-meson.build.patch` — argp probe optional; `intl` optional and
   `ENABLE_NLS` defined only when intl is found; `harmonyos` added to the
   include-directory branch.
2. `0001-lib-libdvbv5-dvb-dev-local.c.patch` — udev monitor thread: stop flag
   + `pthread_join` instead of `pthread_cancel`.
3. `0002-lib-libdvbv5-dvb-dev-remote.c.patch` — remote receiver thread:
   socket `shutdown()` + `pthread_join` instead of `pthread_cancel`.
4. `0003-lib-libv4lconvert-libv4lconvert.c.patch` — `V4L2_PIX_FMT_NV12_16L16`
   fourcc fallback.

None of the patches introduces a platform conditional-compilation macro. The
two thread patches are unconditional POSIX rewrites; the fourcc patch uses the
standard `#ifndef <UAPI_MACRO>` availability check, and the Meson patch uses
feature probes (`cc.has_function`, `dependency().found()`,
`host_machine.system()`) rather than platform macros.

## Build log of the failure → fix cycle

| Step | Command | Observed first error | Root cause | Fix |
|---|---|---|---|---|
| 1 | `meson setup` | `C shared or static library 'argp' not found` | musl has no argp; probe is hard | argp probe → `required : false` |
| 2 | `meson setup` | `Dependency "intl" not found` | musl has no usable libintl; dep is hard | `intl` → `required : false` |
| 3 | `ninja` | `'gettext.h' file not found` | OHOS reports `harmonyos`, so top-level `include/` is not on the path | add `harmonyos` to that branch |
| 4 | `ninja` | `use of undeclared identifier 'V4L2_PIX_FMT_NV12_16L16'` | OHOS UAPI header gap | fourcc fallback |
| 5 | `ninja` | `incompatible integer to pointer conversion` in `gettext.h` | `-DENABLE_NLS` forced the libintl branch with no libintl | define `ENABLE_NLS` only when `dep_intl.found()` |
| 6 | `ninja` | `undefined symbol: pthread_cancel` | musl has no thread cancellation | cooperative stop / `shutdown` + `pthread_join` |
| 7 | `conan create` | `Dependency "libudev" not found` | dependency's `.pc` was not generated | add `PkgConfigDeps(self).generate()` |

Result: `ninja` builds 105/105 targets; `libdvbv5.so.0.0.0` links with
SONAME `libdvbv5.so.0`.

## Verification

```bash
conan create archives/l/libdvbv5/1.32.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  -r=ohpcd --build=missing
# exit 0
```

Agent verification notes:

- Log path: `reports/conan-create.log`（最终一次 `conan create` 的完整原始输出，4801 行）
- `test_package` output: `checks=19 failures=0` / `RESULT: PASSED`
- Upstream test log: `reports/upstream-test.log` (`No tests defined.`)
- Upstream round-trip log: `reports/upstream-roundtrip.log`
- Log SHA256: `70daa5a0131e6834c199eece386fe952e52f80a8e1e3ae9cf9f9014031888188`
  （核验命令：`sha256sum archives/l/libdvbv5/1.32.0/reports/conan-create.log`）

## OHOS-specific test

`test_package/test_libdvbv5.c` contains `test_ohos_packaging`, asserting that a
consumer binary built against the packaged library links and executes on OHOS.
That can only succeed if `package()` signed the ELF and materialised
`libdvbv5.so.0`; upstream covers neither.

## Knowledge graph usage (W5)

Four problem classes were matched against the knowledge graph using the real
error strings from the build. Cross-checked against each entry's
`error_signature` / `root_cause`:

| Problem (actual error text) | Entry | Applicable |
|---|---|---|
| `undefined symbol: pthread_cancel` | E085 (`undefined reference to pthread_cancel`; musl has no POSIX thread cancellation) | yes |
| `Dependency "intl" not found (tried builtin and system)` | E508 (signature covers `host_machine.*harmonyos` and `implicit declaration.*dgettext`) | yes |
| `-DENABLE_NLS` + gnulib gettext rename → implicit `dgettext` | E142 (`g_libintl_dgettext: symbol not found`; root cause is `-DENABLE_NLS` with gnulib gettext renaming) | yes |
| Meson platform branch missing `harmonyos` → `gettext.h` not found | E355 (`host_machine.system()` returns `harmonyos`, must map to the linux branch) | yes |

The `argp` hard probe did **not** match any accurate entry — the nearest hit
(E139) is about GMP static-only packaging and is unrelated. The
`required : false` fix came from engineering judgement, not from an entry.

**No new knowledge draft was created**: all four classes are covered by
existing entries, so this adaptation is 路径 A (基础适配), not 路径 B
(贡献创新). `git diff --name-only upstream/main...HEAD | grep knowledge` is
empty.

## Pending optional verification

Runtime DVB behaviour (frontend tuning, demux, service scan) needs a host with
`/dev/dvb/adapter*/frontend*` and a live signal; this worker has none. R40
adaptation completeness for those runtime paths still requires manual
confirmation on suitable hardware.
---

**编译结束**: 2026-09-22 10:35
**最终状态**: built
