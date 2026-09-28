# libconvolve 0.0.8 adaptation notes

- Source: upstream Heaven/SourceForge release, downloaded from the established
  linuxaudio.org source mirror. SHA-256 matches the FreeBSD port distinfo.
- W0: `conan download --only-recipe` and `conan install --build=never` succeeded
  on HarmonyOS PC for `fftw3f/3.3.10`, `libsndfile/1.2.2`, and
  `libsamplerate/0.2.2`. The distinct `fftw/3.3.11` package only provides
  double-precision `libfftw3`, so it cannot satisfy the upstream `fftwf_*` API.
- Build: serial GNU Make, static target only. `make -B` forces a fresh archive;
  the upstream tarball itself contains an unrelated prebuilt `libconvolve.a`.
  `-DC_CMUL` selects the upstream portable C path instead of optional libDSP.
  `-fgnu89-inline` makes legacy `complex_mul` emit a linkable symbol under
  Clang 15. Header injections supply declarations omitted by old source files.
- The public `convolve.h` includes `fftw3.h`; Conan therefore propagates
  `fftw3f` headers to consumers. The other two libraries are link dependencies.
- Upstream test: `ringbuffer_test.c` is the only test source. Its Makefile rule
  mentions nonexistent `convolve.c`, and the source omits `ringbuffer.h`.
  The recipe compiles it unchanged with `-include ringbuffer.h`, then runs it.
  It is a smoke program without assertions, so its success means exit code 0,
  not comprehensive ring-buffer correctness.
- Consumer test: links the installed archive, runs impulse convolution, loads
  a tiny valid WAV with `load_response`, checks decoded data and cleanup.
  This exercises both the public header and transitive dependency linkage.
- The upstream impulse output is approximately 0.333333 for a unit impulse
  because its normalization factor is `chunk_length * 6`. The recipe does not
  change upstream numerical behavior.
- License metadata is inconsistent upstream: source-file notices say
  LGPL-2.1-or-later, while the bundled `LICENSE` file is GPL-2.0 text. The
  package declaration conservatively follows the bundled LICENSE; no claim
  of a relicensing decision by the upstream author is made here.
- No upstream source or test file was modified. No patch is applied.
- Final device validation: upstream smoke 1/1 and added consumer test 1/1.
  The local-only `conan create` log has SHA-256
  `046e147c9ef10b423567bee950586f345afddd5c8734f0e81f5a367bd5a28ab3`;
  build logs and test reports are not included in the PR.
