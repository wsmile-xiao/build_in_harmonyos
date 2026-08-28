# elfutils 0.191

The recipe builds only `libelf` (static `libelf.a` plus `gelf.h`/`libelf.h` and
the `elf/` headers) for OHOS armv8. The elfutils tools are not built because
they require GNU `argp`, which is unavailable on OHOS.

Patches cover OHOS portability:
- `config.sub`: recognize `aarch64-linux-ohos` (OS `ohos` and the `linux-ohos`
  kernel combination).
- `lib/eu-config.h`: make the `_()` gettext macro identity because gettext is
  unavailable on OHOS.

The shipped `configure` is adjusted at build time: the `argp_parse` check is
made non-fatal and hmdfs temp dirs use `umask 000`.

## Test Status

`test_package/test_elf.c` links the packaged static library and verifies both
the supported `elf_version(EV_CURRENT)` path and rejection of `EV_NONE`.
The full upstream elfutils test suite is not run because this recipe builds
only libelf and omits the GNU-argp-dependent tools.
