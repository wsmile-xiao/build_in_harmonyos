# Yavta 0.0-git20260603.4257331 adaptation notes

- The source is the unmodified upstream snapshot corresponding to commit `42573311466dbeab630d084bc2d5afe88154690b`. It is downloaded from Canonical's Ubuntu archive and pinned by SHA256 in `conandata.yml`. The extracted seven-file source tree was compared byte-for-byte with the official Git commit; no file differences were found.
- The upstream project is a small C application built with Meson. It bundles its V4L2 UAPI headers and has no external Conan dependencies.
- The exact source archive contains no `tests/` or `test/` directory, no test-like source files, and no `test()` registration in `meson.build`. The upstream test count is zero; the inventory is recorded in `test_package/MANIFEST.yml`.
- The Conan test runs the packaged `yavta --help` binary and checks its usage and `--help` output. It is designed to run in the OHOS Conan test environment using the configured HNP bash wrapper.
- Meson does not copy `tools.build:compiler_executables` archiver settings into its generated native file. The recipe resolves `llvm-ar` from the configured compiler directory or OHOS SDK and pins its absolute path, because CI workers may not expose it on `PATH`.
- Yavta needs a V4L2 device such as `/dev/video0` and suitable device permissions for capture operations; `--help` is safe to run without camera hardware.
