# libcmtspeechdata 2.1.1-git20160721-8efc468 — adaptation knowledge record

This archive records a reproducible HarmonyOS PC build of the 2016 libcmtspeechdata snapshot. It complements the repository's existing general entries E160 (GNU config.guess/build-host mapping), E011 (HMDFS temporary directory permissions), and draft E571 (libcheck `TEMP` selection). The points below are specific observations for this package and are not a new Path B claim.

## Source coordinate

Use Debian's exact orig archive for `2.1.1+git20160721~8efc468`, not a moving branch. The task-facing Conan version remains `2.1.1-git20160721-8efc468`. The downloaded archive SHA-256 is `4f01aeba95fbe2c87193e41fd3eb414f0599c00b0a021411a514d797fc7acb05`.

## Reproducible build lessons

1. **Bootstrap in the source directory.** This Debian orig archive includes `configure.ac` but omits generated Autotools files. Run `autoreconf -fi` with `cwd=self.source_folder`; running it from Conan's build directory fails with `configure.ac is required`.
   Declare `autoconf/2.72`, `automake/1.18`, and `libtool/2.5.4` as Conan `tool_requires`; the CI worker's system bootstrap lacked `aclocal`, and its system Autoconf Perl modules were incomplete (`Autom4te/FileUtils.pm`). On OHOS, invoke the package tools explicitly with native Perl and matching macro paths: the packaged Perl binary is ABI-incompatible, and the relocatable Automake wrappers need their package `share` directories supplied.
2. **Pass the GNU system triple explicitly.** Device `uname -s` is `HarmonyOS`, which generated `config.guess` cannot classify. Configure with `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu` (the existing E160 pattern).
3. **Relax generated config.status temp permissions.** HMDFS rejects the `confXXXXXX/subs1.awk` write after Autoconf creates the directory with `umask 077`. After bootstrap, replace `umask 077` with `umask 022` in generated `configure`, matching E011.
4. **Supply package metadata for the utility targets.** The registered `dbus/1.14.10` package has no `dbus-1.pc`; set `DBUS_CFLAGS` and `DBUS_LIBS` from Conan package metadata. The default `make all` also compiles `utils/cmtspeech_ofono_test`, whose source includes PulseAudio but whose Makefile target omits those flags. Pass private `pulseaudio/17.0.1` include/library paths and Expat's transitive library path.
5. **Make Check's runtime files writable.** libcheck prefers `TEMP`, then musl `P_tmpdir` (`/tmp`), then `TMPDIR`; setting only `TMPDIR` cannot override the read-only `/tmp`. Set `TEMP` to a writable build directory and activate Conan's build environment while running `make check`, so Check's dynamic library is found. Upstream sets its XML report path to `/tmp/result.xml`; the declared patch relocates only this report to the writable test directory.

## Evidence

HarmonyOS aarch64 `conan create` exited 0. `make check` ran both upstream programs: `test_ring` reported 2 checks passed, `test_cmtspeech_msgs` reported 8 checks passed; Automake summary was 2/2, with 0 failures/errors. The installed-package consumer called the public `cmtspeech_msg_encode_reset_conn_req` API and verified the control message type, domain, and encoded byte layout.
