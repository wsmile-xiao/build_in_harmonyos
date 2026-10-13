# liquidsfz 0.4.1 on HarmonyOS

HarmonyOS-specific regression test: `test_liquidsfz_ohos` checks the actual `HarmonyOS`/`aarch64` runtime, uses a temporary directory under `/storage/Users/` with group read/execute permission for HMDFS, and loads an SFZ from a UTF-8 path containing spaces. Its WAV sample is resolved relative to the SFZ directory; the rendered stereo output must be finite and nonzero. Conan builds this target only for HarmonyOS/OHOS, signs it, verifies the `.codesign` section, and runs it on the device. On 2026-10-10 the case passed (peak 0.0857217), together with the existing generic consumer (peak 0.0846679). This is one additional OHOS-specific case, not a reclassification of the generic consumer.

The official 0.4.1 release tarball includes a generated Autotools configure script. The core static library uses `libsndfile/1.2.2`; optional JACK, LV2, and FFTW integrations are disabled.

HarmonyOS compatibility: the build profile exports GNU Bash as `CONFIG_SHELL`, but Bash fails to resolve the current directory on HMDFS. The recipe invokes configure through `/bin/sh`. The release's old `config.guess` does not recognize HarmonyOS, so configure receives an explicit AArch64 GNU build/host triple. Autoconf's temporary directory created with `umask 077` cannot be written on HMDFS; the recipe uses a build-local `mktemp` wrapper with `umask 027` for configure. Upstream generated files are left unchanged.

Local verification: `conan create` with the repository's `ohos-aarch64` host and build profiles compiles the static library, passes both registered upstream tests (`testsynth`, `testsfzreader`), and runs a Conan consumer that generates a WAV, loads an SFZ region, and renders nonzero audio. Test executables are signed before running on HarmonyOS.
---

**编译结束**: 2026-10-04 22:08
**最终状态**: built


Test counting correction (rule4): Automake's 2/2 result counts executables, not functional cases. The recorded testsynth.log contains 10 executed non-FFTW groups (basic note, volume, phase, ext cc, silence trigger release, noise, 2control, interpolation time align, end opcode, eq opcode); testsfzreader.log contains 10 parser inputs checked against expected output. Thus the executed upstream functional-case result is 20/20, plus one passing consumer case. Both executables exited 0; test-suite.log records FAIL=0 and ERROR=0.

The upstream tests directory also contains a separate inventory of 12 source files: 11 C++ programs and gen-upsample.py. Eight manual diagnostic programs are not registered in TESTS and were not executed in this verification (testcurve, testenvelope, testxf, testfilter, testhydrogen, testliquid, testmidnam, testperf). They need parameters/fixtures or interpretation of diagnostic output; testcurve also has unexecuted deduplication assertions. testupsample requires FFTW and is disabled by the current configure options. gen-upsample.py uses SciPy to generate FIR code and is not a PASS/FAIL test. FFTW-only branches inside testsynth (tiny_loop, wav_loop, pitch, width and FFT assertions) are also not executed with HAVE_FFTW=0. These exclusions are not counted as passes.
