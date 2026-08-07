# aalib 1.4p5 OpenHarmony adaptation

## Source

The source archive is the Debian `aalib_1.4p5.orig.tar.gz` archive. Its
embedded source directory is `aalib-1.4.0`.

## Adaptation

- Disable X11, SLang, and curses drivers to keep the recipe free of Conan
  runtime dependencies.
- Accept the `aarch64-linux-ohos` Autoconf triplet in the bundled `config.sub`.
- Make the bundled libtool setup use `host` when `target` is empty during
  cross compilation.
- Limit the OpenHarmony recipe to the armv8 profile.

## Verification

- `make check`: completed successfully; upstream ships no test cases.
- `test_package/aalib_smoke`: 1/1 passed on the OpenHarmony device.
