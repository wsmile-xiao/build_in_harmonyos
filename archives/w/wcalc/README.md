# wcalc

wcalc is an arbitrary-precision command-line scientific calculator. It supports arithmetic expressions, variables, alternate number bases, unit conversion and interactive standard input. Its license is GPL-2.0-or-later.

## OpenHarmony PC adaptation

The Conan recipe builds wcalc 2.5 with the native OHOS Clang toolchain. It uses the published `gmp/6.3.0` and `mpfr/4.2.2.1` Conan packages. Readline is disabled because this adaptation does not add a readline dependency; command history and completion are therefore unavailable. Standard input remains usable.

The released Autoconf `configure` script creates a temporary directory with `umask 077`. On OHOS HMDFS, `config.status` then cannot write `subs1.awk` there. The OHOS-only patch changes that directory creation to `umask 022`.

The [OHPCD PR build 63647](https://ohpcd.atomgit.com/buildbot/#/builders/1/builds/63647) built and tested commit `66df5ab2` on OHOS armv8. `make check` reported 12 PASS, 9 XFAIL, 0 FAIL and 0 ERROR; the packaged command passed seven consumer checks. The package is built and tested, but its binary has not been uploaded to the public Conan registry.

Upstream project: https://sourceforge.net/projects/w-calc/
