# pchar 1.5 OHOS adaptation notes

pchar ("Path Char") is a 1997–2005 network path characterization tool from
Sandia National Laboratories (U.S. DOE): it probes a destination host with
ICMP, UDP and/or TCP packets and reports RTT, jitter and loss statistics
plus a slope/intercept regression result table.

## Upstream
- Source: http://www.kitchenlab.org/www/bmah/Software/pchar/pchar-1.5.tar.gz
- Build: plain autoconf (2001 era, autoconf 2.13 generation) + Makefile.in
- The upstream tarball has no bundled test suite or `make check` target. The recipe adds one offline replay regression against the upstream executable; it processes two saved IPv4 probe records and asserts one-hop path-analysis output.
- License: U.S. government work — Sandia dedicates the software to the
  public, provided as-is (see README)

## OHOS problems and fixes (patches/)
1. `config.guess` / `config.sub` (2001) do not know HarmonyOS
   (`uname -s` = `HarmonyOS`) or aarch64: added a `*:HarmonyOS:*:*)`
   branch emitting `aarch64-unknown-linux-ohos`, and accepted
   `linux-ohos*` / aarch64 / arm64 in `config.sub`.
2. The device filesystem is case-insensitive: the tarball ships a file
   named `VERSION`, and with `-I$(srcdir)` on the include path the C++
   standard header `<version>` (pulled in via libc++) resolved to it.
   Dropped `-I$(srcdir)` from `IFLAGS` (every source includes only
   headers from its own directory).
3. `pc.h` defines `typedef enum {false, true} bool;` when the configure
   probe reports `SIZEOF_BOOL=0` (which it does for the C++ compiler);
   that redefines the built-in C++ `bool`. Guarded the fallback with
   `!defined(__cplusplus)`.
4. `Makefile.in` ignored `DESTDIR` and installed the program into
   `${sbindir}`; conan installs with `DESTDIR=<package_folder>`.
   Retargeted the install rules to `${DESTDIR}${bindir}` (program) and
   `${DESTDIR}${mandir}` (man page) so artifacts land in the package
   `bin/` / `man/`.
5. `ResultTable.cc`: `abs(partialmins[i] - ...)` is ambiguous between the
   C `abs(int)` and the C++ `std::abs` overloads under libc++; cast the
   arguments to `long`.
6. `Pctest.cc`: `register int sum` — the `register` specifier is removed
   in C++17 (the OHOS profile sets `compiler.cppstd=17`).
7. `main.cc`: only short options existed (`-V`, `-h`); the CI smoke test
   uses `--version` / `--help`. Added a `getopt_long` mapping
   (`--version` → `V`, `--help` → `h`); the OHOS sysroot `getopt.h`
   provides `getopt_long`.

## Verification (on-device, ohos-aarch64 profile, conan-exact flags)
- `./pchar -V` → `pchar 1.5`, exit 0
- `./pchar -h` / `./pchar --help` → usage, exit 0
- `./pchar --version` → `pchar 1.5`, exit 0
- `make install DESTDIR=...` → `bin/pchar`, `man/man8/pchar.8`
- The newly added trace-replay regression still requires a fresh on-device `conan create` run after this recipe change.
