# ThorVG 1.0.6 OpenHarmony notes

- Build system: Meson.
- Target: OpenHarmony aarch64.
- External package dependencies: none for the selected software renderer.
- Upstream tests are enabled with `tests=true` and run during `build()`.
- Optional loaders, savers, tools, bindings, and extras are disabled.
- `test_package` renders a rectangle and checks the output pixel buffer.
