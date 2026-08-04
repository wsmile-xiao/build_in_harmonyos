# bmake 20200710 OHOS Notes

The package uses the upstream `boot-strap` flow and installs the executable plus
the `share/mk` runtime files. Conan run environments set `MAKESYSPATH` to the
packaged mk directory.

The OHOS build filesystem rejects writes to Autoconf temporary directories made
under `umask 077`, so the generated configure script uses `umask 022`. The
platform identifier contains spaces; `MACHINE` is therefore set to `ohos`, and
`HOST_TARGET` is derived from the Conan architecture. Conan's `armv8` setting is
mapped to the upstream `aarch64` name. Other architectures are rejected because
this recipe currently targets OHOS aarch64 only.

The upstream bootstrap unit-tests run through the freshly built bmake binary.
The explicit `ohos-aarch64` host target prevents the HarmonyOS system name from
being used as a build directory. `MK_AUTO_OBJ=no` supplies the otherwise
undefined make variable used by the upstream `mk/obj.mk` conditional. The
consumer test additionally executes the packaged bmake against a generated
Makefile.

On OHOS, `diff` may be an alias and the upstream `which()` helper then returns
an empty path. The bootstrap patch searches `PATH` for an executable `diff`
before the unit-test output comparison step.
