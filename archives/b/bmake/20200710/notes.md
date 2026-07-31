# bmake 20200710 OHOS Notes

The package uses the upstream `boot-strap` flow and installs the executable plus
the `share/mk` runtime files. Conan run environments set `MAKESYSPATH` to the
packaged mk directory.

The OHOS build filesystem rejects writes to Autoconf temporary directories made
under `umask 077`, so the generated configure script uses `umask 022`. The
platform identifier contains spaces; `MACHINE` and `HOST_TARGET` are therefore
set to `ohos` and `ohos-aarch64` respectively.

The upstream bootstrap unit-tests require NetBSD mk behavior and fail when run
with the OHOS system mk search path. The recipe still builds, installs, and
packages bmake, while the consumer test executes the packaged bmake against a
generated Makefile.
