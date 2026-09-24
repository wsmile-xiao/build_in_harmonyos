# libaudec

libaudec is the audio file decoding/resampling wrapper library from the
Zrythm project: it wraps libsndfile (WAV and friends) and a bundled
minimp3 decoder behind one `Audec*` C API, with optional resampling via
libsamplerate.

## OHOS adaptation

- Meson build with `tool_requires` meson/1.11.0 + ninja/1.12.1 (no
  ambient meson on the OHOS device/worker).
- Dependencies from the local registry: `libsndfile/1.2.2`,
  `libsamplerate/0.2.2` (upstream minimums: sndfile >=1.0.25, samplerate
  >=0.1.8). The ffmpeg backend is commented out upstream; mp3 decoding
  uses the bundled minimp3 headers, so there is no ffmpeg/glib
  dependency.
- Static-only delivery (R26): upstream's `both_libraries()` also builds
  a shared libaudec.so that cannot link — the ohpcd libsamplerate static
  library is non-PIC (`R_AARCH64_ABS64` relocations). Patch 0001 turns
  it into `static_library()`.
- pkg-config bridging: `samplerate.pc` alias generated via
  PkgConfigDeps `pkg_config_aliases` (the libsamplerate package sets no
  pkg_config_name); PKG_CONFIG_PATH injected explicitly.
- Upstream tests (3, `meson test`) run inside the package build; one
  extra OHOS consumer test (12 assertions) lives in test_package/.

## Dependencies

- libsndfile 1.2.2
- libsamplerate 0.2.2
- build: meson 1.11.0, ninja 1.12.1

## References

- Upstream: https://github.com/zrythm/libaudec
- Version: 0.3.4
  (`https://github.com/zrythm/libaudec/archive/refs/tags/v0.3.4.tar.gz`,
  sha256 9a53eb292804818ddd8b19f749f64257ca586b54672494daf138092858935115)
