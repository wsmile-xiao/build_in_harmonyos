# tradcpp

tradcpp is David A. Holland's preprocessor that implements the **traditional
(Reiser) preprocessing algorithm** rather than the ISO one.  The difference is
semantic, not cosmetic — modern `cpp` no longer preprocesses the K&R C that
NetBSD's build system still carries:

```sh
$ printf '#define STR(x) #x\nSTR(hello)\n' | cpp         # ISO: stringifies
"hello"
$ printf '#define STR(x) #x\nSTR(hello)\n' | tradcpp     # traditional
#hello
```

- Upstream: https://www.NetBSD.org/~dholland/tradcpp/
- Release: 0.5.3
- License: BSD-2-Clause
- Package form: `bin/tradcpp` + `share/man/man1/tradcpp.1` (application)

## HarmonyOS PC adaptation

The upstream `Makefile` is nine lines long and ends in `.include <bsd.prog.mk>`
— it is a *NetBSD* makefile that requires bmake and that GNU make cannot even
parse.  The recipe adds a `GNUmakefile` (via
`patches/0001-add-GNUmakefile.patch`) and leaves the upstream file untouched:
GNU make prefers `GNUmakefile` over `Makefile`, so the worker builds with plain
GNU make while NetBSD users keep their build.

The nine sources in the added makefile are exactly upstream's `SRCS`; compiler
and flags come from the Conan toolchain (`$(CC)`, `$(CPPFLAGS)`, `$(CFLAGS)`,
`$(LDFLAGS)`).

## Upstream tests

`tests/` is a complete suite: 40 cases (`t01` … `t40`), each an input `tNN.c`
plus a recorded expectation `tNN.good`, compared byte for byte.  All 40 are
executed for real inside `build()` and a mismatch fails the build.  Two details
of upstream's harness are reproduced exactly: the working directory must be
`tests/` (t17/t38 include `subdir/test.h` relatively) and the argument must be
the bare `tNN.c` (t38 asserts `__FILE__`).

See `0.5.3/notes.md` for the full record and `0.5.3/test_package/MANIFEST.yml`
for the per-case audit.
