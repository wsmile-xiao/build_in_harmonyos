# mawk 1.3.4-20260302

mawk is a standalone AWK interpreter implemented in C. It uses Autotools and
has no Conan runtime or build requirements. On HarmonyOS the recipe passes an
explicit `aarch64-linux-ohos` host triplet because the upstream config.guess
does not recognize HarmonyOS directly, while config.sub accepts linux-ohos.

HarmonyOS real-device verification completed successfully: upstream `make
check` passed 174/174 checks, and the installed-package consumer test passed
3/3 assertions.
## HarmonyOS Notes

- Configure is invoked with explicit GNU/Linux build and HarmonyOS host triplets because the bundled `config.guess` does not recognize HarmonyOS.
- `CC=clang` is required because the device does not provide a `cc` alias.
- Autoconf's random `mktemp` directory is replaced with a fixed directory under the Conan build folder because HarmonyOS MAC rejects the random-name creation path.
- The upstream `make check` suite is executed without suppression. OHOS builds use Clang built-in Inf/NaN classification in mawk's existing formatter and POSIX comparison branch because the device configure probes do not expose the symbols.
- After configure, `man/Makefile` is patched at bytes level to force `INSTALL = ../install-sh -c`; this avoids non-UTF-8 `mktemp` noise from polluting the detected `INSTALL` variable and breaking `make install` in the man subdirectory.
