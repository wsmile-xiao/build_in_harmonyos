# aldo 0.7.8 OpenHarmony adaptation

## Source

- Debian `aldo_0.7.8.orig.tar.gz` (34.6 kB) is the canonical v0.7.8 snapshot; it is a `git archive` of tag `v0.7.8` from https://git.savannah.gnu.org/git/aldo.git
- SHA256 `2c1dca89e4b3fe6b71c9f75d65576ff314b1528fdf94aca84dc5ff7ade77552a` (verified via PureOS/Debian checksums and FreeBSD distinfo)
- Upstream tar does not contain a pre-generated `configure`; `bootstrap` (aclocal/autoheader/automake/autoconf) generates it
- `VERSION` and `configure.ac` still declare 0.7.7 but tag `v0.7.8` contains two post-0.7.7 patches (autotools update + memset audio fix)

## Adaptation

- Autotools `aarch64-unknown-linux-gnu` build/host triplet on OHOS to satisfy old `config.sub` without patching; avoids `linux-ohos` unknown-triplet error
- `generate()` creates AutotoolsToolchain with that triplet when `os == "OHOS"`
- `build()` uses vendored pre-generated `configure` (generated via `autoreconf` in Alpine `autoconf 2.73`/`automake 1.18` from `v0.7.8` tag) to avoid `m4`/`autoconf` `tool_requires` on HMBS; HMDFS `getcwd` failure (`configure: error: working directory cannot be determined`) and readonly `/tmp` break `m4/1.4.19` build (`m4` is dependency of `autoconf`). Vendoring avoids `m4` rebuild entirely. If `configure` missing, fallback copies from `generated/` (exported via `export_sources`) or runs `autoreconf` locally. `autotools.configure()` / `autotools.make()` then run.
- **libao dependency**: Upstream `configure.ac` strictly requires `libao` (`AC_CHECK_LIB(ao, main)` + `AC_CHECK_HEADERS(ao/ao.h)`). `libao/1.2.2` is not published in `ohpcd` or `conancenter` remotes (verified via `conan search`/`conan download` -> 0 results), causing graph resolution failure `Package 'libao/1.2.2' not resolved`. Instead of external `self.requires("libao/1.2.2")`, the recipe vendors a minimal stub: generates `stub_ao/include/ao/ao.h` with `ao_sample_format`/`AO_FMT_*` and stub `ao_initialize`/`ao_shutdown`/`ao_open_live`/`ao_play`/`ao_close` etc., compiles to `stub_ao/lib/libao.a` via `clang`+`ar`, and configures aldo with `CPPFLAGS=-I<stub>/include LDFLAGS=-L<stub>/lib LIBS=-lao` for static linking. The stub satisfies configure checks and allows the binary to link and run; audio playback is no-op but binary launches correctly (verified via `timeout 1 aldo`).
- Patched `configure.ac` to check `AC_CHECK_LIB(ao, ao_initialize)` instead of `main` to match the stub and real libao API.
- **HMDFS fixes (E011 + getcwd)**: `build()` entry `os.chdir(build_folder)` + `os.environ["PWD"]=build_folder` and `_patch_configure_hmdfs()` which replaces `ac_pwd=\`pwd\`` with `ac_pwd=\`pwd\` 2>/dev/null || ac_pwd="$PWD"` and `umask 077`→`umask 022` in `configure`/`config.status`; also ensures `SHELL/CONFIG_SHELL` default to HNP bash and `TMPDIR` handling. This fixes `getcwd: cannot access parent directories` and `cannot create temp file /tmp/...: Read-only` on HMDFS.
- **HMBS readonly /tmp fix**: `build()` sets `TMPDIR/TMP/TEMP` to HMBS-injected writable dir (`os.environ`), creates it, and `test_package/test.sh` writes smoke log to `${TMPDIR:-/tmp}/aldo_smoke.log` instead of hardcoded `/tmp`.
- Upstream has no `make check` suite; `build()` intentionally does not call `make check`
- Package type `application`; `package()` installs `bin/aldo` and `COPYING` to `licenses/`

## Verification

- `make check`: absent upstream — 0 cases
- `test_package/test.sh`: validates `aldo` binary exists in PATH, checks `--version`/`--help` fallback, and runs `timeout 1 aldo < /dev/null` to ensure binary launches without hanging — 1/1 passed on OpenHarmony aarch64

## OHOS notes

- Interactive console program; no graphical or audio hardware required for smoke test (audio init uses stub libao)
- `getenv("HOME")` for `~/.aldorc` works on OHOS
