# VolPack 1.0b3 HarmonyOS PC adaptation

The Stanford release is `volpack-1.0b3.tar.Z` (SHA256
`d7cfd5f6819cccf88363d2270377e547a07f35da6a0dac45845ecc1640e410fa`).
The OHOS Toybox `gzip` cannot decode its historical LZW `.Z` format.
The recipe therefore uses Debian's versioned `orig.tar.gz` mirror, whose
VolPack C sources, public header, MRI fixture and reference PPM were checked
byte-for-byte against Stanford's release. Debian updated the Autotools files;
the library implementation and four upstream rendering tests are unchanged.

The bundled 2007 `config.guess`/`config.sub` did not recognize either AArch64 or
HarmonyOS. The patch recognizes the real native `aarch64-unknown-linux-ohos`
triple. Configure and Make also require a writable `TMPDIR` because `/tmp` is
read-only on the target.

Hosted CI #63564 exposed a separate HMDFS issue: Autoconf's generated
`config.status` creates a mode-0700 `confXXXXXX` directory whose mapped owner
cannot write its temporary sed files on that worker. The OHOS-only Conan build
now applies the same guarded, group-writable scratch-directory substitution
used by the passing libctl recipe. Both original templates must occur exactly
once, so an upstream configure change fails closed rather than silently
skipping this compatibility fix.

For Conan's separate build directory, the original `./makeopts` target is
incorrect. Patch both `Makefile.am` and the distributed `Makefile.in` to invoke
`$(srcdir)/makeopts` so the build works without requiring automake on the PC.
The Debian build's install target omits the public `volpack.h`; the Conan
package copies it from the source tree so downstream consumers can compile.

`make check` has no executable tests in this release. The package build also
runs all four paths in `examples/test.csh` via a portable `sh` script, comparing
each output byte-for-byte with upstream `check.ppm`; all four passed in the
initial native exploratory build and again in a clean `conan create` on
2026-09-28. A separate consumer test linked the packaged library and passed
its public context and volume-state API assertions.

Stanford's distribution page states that downloads since 2007 use BSD-3-Clause.
The source archive still preserves the older, superseded no-sale notice; the
package includes the current Stanford license text and link.

## 编译结束

Native OHOS/aarch64 Conan create, four upstream rendering paths, packaged
consumer test, and target-local W3 CI simulation passed on 2026-09-28.
Hosted CI #63564 failed at `config.status`; the corrected recipe subsequently
passed the full target-local CI simulation (1/1) on 2026-09-28. Hosted CI
rerun and artifact publication remain pending.
