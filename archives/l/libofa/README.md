# libofa

LibOFA (Library Open Fingerprint Architecture) is an open-source audio
fingerprint library by MusicIP: it turns PCM audio into a compact text
fingerprint that the MusicDNS service can identify. The public C API is two
functions in `ofa1/ofa.h`: `ofa_get_version()` and `ofa_create_print()`.

## OHOS adaptation

- **Build system**: autotools `configure` + `make` (2005-era generated files kept, no autoreconf).
- **Triplet**: the bundled `config.guess` (2005-04-22) knows neither aarch64 nor
  HarmonyOS, and the bundled `config.sub` mangles `-linux-ohos`; both are fixed
  with early-exit portability patches (same family as `libbrahe/1.3.2`).
- **Temp dirs**: `configure` uses `umask 077` for its `config.status` scratch dir,
  unwritable under HMDFS uid mapping; patched to `umask 022`.
- **Examples**: `examples/protocol.cpp` included `<curl/types.h>`, removed from
  modern curl; `wavefile.cpp`/`uselame.cpp` missed `<unistd.h>` (same fixes as
  Debian patches 07/08). Examples are `noinst` demos, so the installed package
  stays a pure library.
- **Upstream tests**: none — no `tests/` directory and no `TESTS` registration
  in any `Makefile.am`. `make check` runs trivially (zero cases); functional
  coverage comes from the `test_package` consumer test (version + real
  fingerprint generation on synthetic PCM, determinism included).

## Dependencies

- expat 2.8.2.1 (XML metadata parsing)
- curl 8.15.0 (MusicDNS HTTP client)
- fftw 3.3.10.1 (FFT backend)

## References

- https://code.google.com/archive/p/musicip-libofa/
- Debian source package `libofa` (patches 01-09 consulted for modern-toolchain fixes)
