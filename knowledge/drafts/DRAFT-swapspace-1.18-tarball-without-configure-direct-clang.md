# DRAFT: swapspace 1.18 — tarball without configure/config.h → direct clang

- **package**: swapspace/1.18
- **context**: autotools project whose release tarball ships only `configure.ac`
  (no generated `configure`) and only a hand-maintained `config.h.static`
  (no generated `config.h`)
- **verdict**: works — no autotools needed, no source patch needed

## error_signature

Build fails either at `options_okay()`/config parsing with

```
opts.c:254:7: error: use of undeclared identifier 'PACKAGE_VERSION'
opts.c:254:29: error: use of undeclared identifier 'PACKAGE_STRING'
```

or, when the recipe passes `-D` values by string concatenation, with a
confusing argv split:

```
clang: error: no such file or directory: 'Jan'
clang: error: no such file or directory: '22'
clang: error: linker command failed ... duplicate symbol: main
```

## root_cause

1. `AC_INIT` values reach the program only through the autoheader-generated
   `config.h`. A tarball without `configure` also has no `config.h`, so
   `PACKAGE_NAME` / `PACKAGE_VERSION` / `PACKAGE_STRING` are simply undefined.
2. `self.run()` goes through a shell. A `-D` macro whose value contains a
   space (`DATE="Sat Jan 22 2022"`, `PACKAGE_STRING="swapspace 1.18"`) must be
   shell-quoted, or the value splits into separate argv words.
3. Autotools `noinst_PROGRAMS` (here `hog`, its own `main()`) are separate
   link targets; folding their objects into the main program's link produces
   `duplicate symbol: main`.

## rec_approach

- Skip autotools for small C programs. Reproduce the target/source mapping of
  upstream's hand-written `Makefile.static` with one clang call per
  translation unit. Avoids an `autoreconf` `tool_requires` chain
  (autoconf/automake/m4/perl) used only to regenerate a build system for a
  handful of files, and removes a CI failure mode instead of adding one.
- Reuse the shipped static `config.h` (`config.h.static` → `config.h`) instead
  of patching sources, and supply the `PACKAGE_*` identifiers as `-D` flags
  with the same values `AC_INIT` declares, so `--version` output matches the
  upstream release.
- Shell-quote every `-D` flag: `'-DDATE="Sat Jan 22 2022"'`.
- Link `noinst_PROGRAMS` helpers as separate link steps; build them (to stay
  faithful to `make all`) but do not package them if upstream's `install`
  target does not.
- Keep `-std=gnu99` when the code uses POSIX `sigaction()` under `-pedantic`.

## rec_command

```python
config_h = os.path.join(src, "config.h")
shutil.copyfile(os.path.join(src, "config.h.static"), config_h)
cc = self.conf.get("tools.build:compiler_executables", default={},
                   check_type=dict).get("c", "clang")
cflags = ["--std=gnu99", "-O2", "-Wall", "-DSUPPORT_LARGE_FILES",
          "'-DVERSION=\"1.18\"'", "'-DDATE=\"Sat Jan 22 2022\"'",
          "'-DVARPREFIX=\"/var\"'", "'-DETCPREFIX=\"/etc\"'",
          "'-DPACKAGE_VERSION=\"1.18\"'",
          "'-DPACKAGE_STRING=\"swapspace 1.18\"'"]
```

## verification

`conan create` exit 0; 20/20 consumer assertions; `readelf` shows ELF64
AArch64 PIE, `GNU_STACK RW` (NX), single `NEEDED libc.so`.

## pitfall: prefix-style macros are *parents*, not final directories

When reconstructing `VARPREFIX` / `ETCPREFIX`-style macros, check how the
source actually consumes them before picking a value. Here:

```c
/* src/swaps.c */
static char swappath[PATH_MAX] = VARPREFIX"/lib/swapspace";
/* src/opts.c */
static char configfile[PATH_MAX] = ETCPREFIX"/swapspace.conf";
```

`VARPREFIX` is the *parent*, so it must be `/var` (yielding
`/var/lib/swapspace`, matching `Makefile.am`'s
`$(localstatedir)/lib/swapspace`). Passing `/var/lib` compiles the doubled,
wrong `/var/lib/lib/swapspace` into the binary.

This class of bug is invisible to tests that always pass an explicit `-s` /
`-c`, because every such assertion still passes. Assert on the **compiled-in
default** — and match the literal path, not just the exit code: an exit-code
check cannot distinguish two different *nonexistent* paths, so both the
correct and the doubled build pass it.

```sh
# discriminates: only the correct VARPREFIX contains /var/lib/swapspace
swapspace -i 2>&1 | grep -q "'/var/lib/swapspace'"
```

The same discipline applies to the packaged data files: install the sample
config where the binary actually reads it, not where it seems tidier.

## pitfall: SDK `libc.so` is a link-time stub

The DevEco SDK sysroot's `libc.so` is a ~72 KB **stub** whose dynamic symbols
all alias to a handful of addresses (`_init`, `_fini`, one shared `ret`
address, `_Exit`). Inspecting it makes every libc function look like an
identical no-op:

```bash
readelf --dyn-syms -W "$SYSROOT/usr/lib/aarch64-linux-ohos/libc.so" \
  | grep -wE "swapon|swapoff"
# both -> 0000000000011d80  (a single `ret`)
```

That address is *not* the implementation. Check a real runtime libc instead
(e.g. `/opt/ohos-guest/lib/libc.so`), where `swapon`/`swapoff` are genuine
28/32-byte syscall wrappers. Concluding "the platform stubbed out swapon"
from the SDK stub alone is a false negative.

## related

- Runtime-scope honesty for kernel-subsystem tools: see the
  `swapspace 1.18` notes.md — build clean, but swap activation needs root +
  `CONFIG_SWAP`, so claim only what was actually asserted.
