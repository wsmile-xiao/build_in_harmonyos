# stk 5.0.1 Adaptation Notes

## Build Strategy

STK provides both CMake and autotools entry points. The autotools flow is used here because it can disable realtime support cleanly:

```bash
./configure --disable-realtime --disable-shared --enable-static --prefix=/
make -C src -j1
```

Only `src/libstk.a` is packaged. The top-level `make` target builds example programs after the library; those examples assume realtime output paths and are not needed for a library package.

## OHOS Notes

- Realtime audio and MIDI backends are disabled to avoid ALSA, JACK, CoreAudio, and device access requirements.
- The package has no external Conan dependency.
- The Conan package is static-only and declares `shared=False` for Conan 2 library metadata.
- STK 5.0.1 ships an older `config.guess`; OHOS builds pass an explicit GNU build triplet to `configure`.
- Autotools `config.status` temp files fail on HMDFS with `umask 077`; the recipe patches `configure` to use `umask 022` before configuration.
- OHOS CI requires runnable ELF files to be self-signed, so `test_package` signs the generated test runner and restores `0755` before executing it.
- Public headers are limited to the offline synthesis, filtering, file I/O, and instrument APIs that are present in `libstk.a`.
- `rawwaves/` is shipped under `share/stk/rawwaves` for consumers that need sample-based instruments.

## Verification

Local host verification compiled `src/libstk.a` and linked a small C++ program using `Stk`, `SineWave`, and `ADSR`. The program generated 256 samples and asserted positive synthesis energy.
