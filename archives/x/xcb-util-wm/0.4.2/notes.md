# xcb-util-wm 0.4.2 adaptation notes

## Source and scope

Official X.Org archive:
`https://xorg.freedesktop.org/archive/individual/lib/xcb-util-wm-0.4.2.tar.xz`.
Its 285152 bytes match SHA-256
`62c34e21d06264687faea7edbf63632c9f04d55e72114aa4a57bb95e4f888a0b`.
The release tarball ships pre-generated `configure` and `Makefile.in`, so no
autoreconf/automake step is needed.

This package is unusual in the xcb-util family because it produces **two
independent libraries with different ABIs**:

| Library | Directory | version-info |
|---------|-----------|--------------|
| `libxcb-ewmh`  | `ewmh/`  | 2:0:0 |
| `libxcb-icccm` | `icccm/` | 4:0:0 |

They are therefore modelled as two `cpp_info` components (`ewmh`, `icccm`)
rather than a single library list, so consumers can depend on either protocol
family independently.

Note that `ewmh/xcb_ewmh.h` is generated at build time from `xcb_ewmh.h.m4`
(and `ewmh.c` from `ewmh.c.m4`); the tarball ships only the `.m4` sources. The
generated header is what gets installed.

## Build behavior

Autotools with `--build/--host=aarch64-unknown-linux-gnu`, shared linking only.
The same two OHOS adjustments as the other xcb-util packages: `umask 077` →
`umask 022` in the generated `configure` (HMDFS directory-permission problem in
`config.status`) and the shebang rewritten to `/data/service/hnp/bin/bash`
(the system `sh` cannot run these scripts).

## Notable adaptation issue: xcbproto_version in xcb.pc

As in `xcb-util`, `XCB_UTIL_COMMON` runs
`pkg-config --variable=xcbproto_version xcb`. Conan's minimal generated `xcb.pc`
lacks the variable, so it is copied in from the real `xcb.pc` in the libxcb
package. Dependency `.la` files are rewritten so `libdir` matches the consumer
copy and bare `.la` references become `-l<name>` flags.

## Validation

`make check` is invoked even though the release ships no test programs, so the
build log carries a trace of the upstream check target.

The consumer test (`test_package/test.c`) links the ICCCM library and exercises
the size-hints setters. These operate purely on the caller's `xcb_size_hints_t`
and implement flag bookkeeping that is worth asserting directly:

- `set_position` / `set_size` **clear both** the `US_*` and `P_*` flags before
  setting exactly one, so calling them twice with different `user_specified`
  arguments must not leave both flags set — the test asserts this mutual
  exclusion, not just the stored `x`/`y`/`width`/`height` values.
- `set_min_size`, `set_max_size`, `set_resize_inc`, `set_base_size` and
  `set_win_gravity` each add exactly their own flag; values are asserted.
- Flags set earlier must survive later setter calls.

The test also touches the EWMH connection struct (`_NET_WM_NAME`) to prove the
`ewmh` component links and its atom table is usable. It needs no X server, and
the assertions are executed via `ctest` from `test()` so the binary is actually
run rather than merely compiled.
---

**编译结束**: 2026-09-19
**最终状态**: built
