# pd-syslog 0.1 — HarmonyOS PC (OHOS aarch64) adaptation notes

## What this package is

`pd-syslog` is the Pure Data (Pd) external `[syslog]`: it takes anything typed
into its inlet, formats it into a single line and forwards it to libc
`syslog(3)` at a severity that can be set through a float inlet. Upstream ships
it as the standard Pd "library template" Makefile plus one C file — six files in
total (`Makefile`, `syslog.c`, `syslog-meta.pd`, `syslog-help.pd`, `README.txt`,
`LICENSE.txt`).

Version `0.1` is not a repo tag: the canonical upstream home
(<https://github.com/umlaeute/pd-syslog>) is explicitly marked as a *temporary*
packaging mirror "to be moved to pkg-multimedia" and tags nothing. The released
0.1 tarball is the one Debian's multimedia team redistributed, so
`conandata.yml` points at `deb.debian.org`'s official source pool (R39), and
`sha256` was taken from the GPG-signed `pd-syslog_0.1-8.dsc` in the same pool:

    7553a7c7601fca5488a0939d1784d0c0329515d454f9f4d02ba70b91f8319e09

The tarball's root directory is `syslog-0.1`, **not** `pd-syslog-0.1`, so
`source()` uses `strip_root=True`.

**License: GPL-2.0-or-later.** `LICENSE.txt` is the GPLv2 text ("either version
2 of the License, or (at your option) any later version"), *not* the BSD license
the surrounding Pd ecosystem usually uses — easy to mis-assume from
`syslog-meta.pd`'s neighbours.

## Build system: six make overrides, zero patches

The upstream Makefile is the Pd library template 1.0.14. It is **not patched**;
everything is injected as make command-line variable assignments, which outrank
any in-file `=`. See `conanfile.py::_make_args()` for the authoritative list and
the reasoning; the six are `UNAME`, `CC`, `PD_INCLUDE`, `prefix`, `LDFLAGS` and
`STRIP`.

### 1. `UNAME=Linux` — required, and invisible on a dev box

The template picks its platform by **exact string match** on `uname -s`
(`Linux` / `Darwin` / `Android` / `CYGWIN` / `MINGW` / `GNU` / `GNU/kFreeBSD`)
and has no OHOS branch. The OHOS worker reports `uname` = `HarmonyOS`, so the
Linux block is skipped entirely: `EXTENSION` stays empty, `PD_PATH` is never
assigned and the link degenerates to `-o syslog.` with no `-shared`, failing
with `ld.lld: error: undefined symbol: main` plus every Pd symbol.

This is the same class of bug pd-libdir/1.11 hit (`system=Linux` there). It does
**not** reproduce on WSL2, which reports `uname` = `Linux`, so a green local
`conan create` proves nothing about it — the override is unconditional for that
reason. Taking the Linux branch is also what produces the artifact name Pd
actually looks for on non-Apple platforms (`pd_linux`), plus
`-fPIC -shared -rdynamic` and `-lc`.

### 2. `PD_INCLUDE` — where m_pd.h lives

Upstream derives `PD_INCLUDE = $(PD_PATH)/include/pd` from `PD_PATH = /usr`,
which only holds for a system-wide Pd install. The recipe overrides
`PD_INCLUDE` directly rather than `PD_PATH`, so it does not have to re-derive
whatever layout the dependency happens to use.

`m_pd.h` comes from the `puredata/0.54.1` package. That package is declared as
an **application** and therefore publishes no `cpp_info.includedirs` even though
it ships `<pkg>/include/pd/m_pd.h`; `_pd_include_dir()` probes both
`include/pd` and `include` for the header and re-exports the directory it found,
so consumers can compile Pd code against pd-syslog alone. This is the pattern
pd-libdir/1.11 established; changing `puredata`'s own recipe would be a separate
PR.

### 3. `STRIP=:` — the host `strip` cannot read the artifact

The template hardcodes

    STRIP = strip --strip-unneeded -R .note -R .comment

and runs it during `make install`. That is the **host** binutils `strip`, and on
a cross build it cannot read the aarch64 ELF it just produced:

    strip: Unable to recognise the format of the input file `.../syslog.pd_linux'

so `make install` dies after the artifacts are already in place. Stripping is
instead requested **at link time** via `LDFLAGS=-Wl,-s`, which uses the same OHOS
clang that produced the file and therefore behaves identically on WSL and on the
worker (verified: the packaged object reports `stripped`, 6.4 KB).

### 4. `LDFLAGS` — DT_SONAME for the local quality gate

`LDFLAGS="-Wl,-soname,syslog.pd_linux -Wl,-s"`. The upstream link line sets no
`DT_SONAME`, which the local SONAME quality gate (L5a) rejects. `-Wl,-s` is the
strip discussed above.

The template's own `-Wl,-rpath,"\$$ORIGIN"` survives as a literal `$ORIGIN`
RUNPATH, which is inert and correct for a plugin: Pd `dlopen()`s it by absolute
path and all its imports come from the Pd process image.

## Pd integration: there is nothing to link against

Pd links itself with `-rdynamic`, so a plugin's undefined Pd symbols are
resolved from the Pd **process image** at `dlopen()` time. Consequences:

- `package_info()` exports no `libs`; only `libdirs`, `defines = ["PD"]` and the
  re-exported `includedirs`.
- The packaged plugin is `lib/pd-externals/syslog/syslog.pd_linux` — upstream's
  own default layout (`/usr/local/lib/pd-externals/syslog`), which is also where
  Pd looks for an extra library, so nothing was renamed or relocated.
- `package_type` is `library` and there is **no** `commands.json`: the plugin has
  no `main()` and installs nothing into `bin/` (R38 does not apply).
- `shared` exists only to satisfy conan's `library` package_type contract and is
  rejected when `False`: Pd `dlopen()`s the plugin and the template has no static
  mode.

Measured with `readelf --dyn-syms` on the packaged artifact:

- exported: `syslog_setup` (Pd's `<classname>_setup` fallback entry point; there
  is deliberately no bare `setup`), plus `_init` / `_fini`.
- imported, GLOBAL UND: exactly the nine Pd symbols `gensym`, `class_new`,
  `class_addanything`, `floatinlet_new`, `getbytes`, `freebytes`, `atom_string`,
  `pd_new`, `s_`, and the libc `syslog` / `openlog` / `closelog`.

`s_` is worth a note: with `PDINSTANCE` undefined (the template only adds
`-DPD -DVERSION`), `m_pd.h` declares `EXTERN t_symbol s_pointer, ..., s_;` — a
plain global of struct type — so `&s_` in `syslog.c` is simply its address. When
`PDINSTANCE` *is* defined the same identifier becomes a macro
(`(pd_this->pd_s_)`) and any shim must not define a symbol for it.

## Tests

**Upstream ships no tests at all.** The tarball has six files, no `tests/`
directory, and the template Makefile defines no `check:` target (`grep '^check'`
over it matches nothing). So the inventory in `test_package/MANIFEST.yml` is
`upstream_test_count: 0` with the evidence recorded, and behaviour is pinned by a
consumer test that is specific to this adaptation.

`test_package/pd_syslog_test.c` is itself a minimal Pure Data runtime: linked
with `-rdynamic` it *defines* the nine Pd entry points above, so the packaged
plugin resolves them to the test process exactly as it would inside a real Pd.
The test then `dlopen()`s the packaged `syslog.pd_linux` with `RTLD_NOW` (so the
load itself proves every import resolves), calls the real `syslog_setup()`, and
drives the real object lifecycle through the recorded Pd callbacks: construct with
the empty selector and with a named selector, read back the `floatinlet_new()`
severity pointer, write `LOG_ERR` into it, send messages, destroy.

`openlog` / `syslog` / `closelog` are **interposed** by the executable (it comes
first in the dynamic symbol lookup scope), so every behavioural assertion is made
on what the plugin actually forwarded — the priority, the ident handed to
`openlog`, and the formatted text — including the exact
`getbytes(strlen(message)+1)` / `freebytes` buffer arithmetic. This is what makes
the test independent of the platform's syslog daemon: **HarmonyOS PC has no
syslogd**, `/dev/log` does not exist, and musl's `syslog()` fails silently, so a
test that waited for a real log line could never pass. 35 assertions, all
executed.

Two upstream behaviours the test pins deliberately, because both are easy to
break and neither is obvious:

- message formatting is `selector` + one space + atoms joined by single spaces,
  and the length arithmetic (`length += argc`) matches only because the code
  emits exactly `argc` spaces;
- a message with an empty selector and no atoms is dropped *before* any
  allocation (`if (length <= 0) return;`).

`gensym` in the shim interns by name and never frees. That is not cosmetic: the
plugin stores the returned `t_symbol *` inside atoms, so a shim that handed out a
fresh slot per call would let a later `gensym()` clobber a symbol an earlier atom
still points at.

## Upstream warnings left in place

`syslog.c` compiles with two warnings under clang 15, both upstream's and neither
patched:

- `syslog.c:92` — `char *buf = s->s_name;` discards `const`, because
  `t_symbol::s_name` is `const char *`;
- `syslog.c:127` — unused parameter `x` in `syslog_free()`.

## Reproduction

```bash
conan create archives/p/pd-syslog/0.1 --name=pd-syslog --version=0.1 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
```

After editing `conanfile.py`, run `conan remove pd-syslog -c` first: a stale
binary in the cache makes `conan create` reuse the previous build, so "all green"
would be evidence about the *previous* recipe.
