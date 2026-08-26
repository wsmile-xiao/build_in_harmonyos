# E260 Draft - GNOME/Meson GLib Consumer Pattern on OHOS

## Context

ATK 2.28.0.1 packages upstream ATK 2.28.0, a small GNOME Meson library that
consumes GLib/GObject and installs headers, pkg-config metadata, translations, and
`libatk-1.0.so*`. The adaptation exposes a reusable pattern for similar GNOME
libraries where the build logic is small, but GLib tooling and the OHOS runtime
environment need recipe support.

Reference library: `atk/2.28.0.1`

Reference shadow CI run: `codex-atk-atk-2.28.0.1-shadow-20260825-1-conan-queued-20260825-232357-19109`

## Observed Issues

1. ATK 2.28.0 declares `version: '2.28'` in `meson.build`, but the same file reads
   `version[2]` to compute the micro version. Patch the project version to `2.28.0`.
2. Meson reports the OHOS host as `harmonyos`, so upstream checks like
   `host_machine.system() == 'linux'` do not trigger even when the linker flags are
   compatible with OHOS.
3. Older ATK Meson options are `disable_introspection` and `enable_docs`; newer
   `introspection`/`docs` names are not portable across ATK releases.
4. Meson's GNOME module expects GLib helper variables such as `glib_mkenums` and
   `glib_genmarshal` from pkg-config metadata.
5. GLib helper scripts can be present in dependency `bin/`, but their `/usr/bin/env`
   shebang may be unreliable in the tested OHOS runner environment.
6. GLib i18n headers can expand gettext calls to `g_libintl_*`; ATK can resolve those
   symbols by linking the `libintl` shipped with the selected GLib package.
7. Shared-library symlinks can be unreliable on OHOS filesystems, so recipes may need to
   create soname aliases with copy fallback.
8. Installed OHOS ELF shared libraries may need `binary-sign-tool` signing before runtime
   smoke tests can execute.

## Recommended Recipe Shape

Use `PkgConfigDeps` and `MesonToolchain`.

Recommended Meson options for ATK 2.28-style packages:

```python
toolchain.project_options["wrap_mode"] = "nodownload"
toolchain.project_options["default_library"] = "shared" if self.options.shared else "static"
toolchain.project_options["disable_introspection"] = True
toolchain.project_options["enable_docs"] = False
```

Recommended supporting helpers:

- Augment generated `glib-2.0.pc` and `gobject-2.0.pc` with `glib_mkenums`,
  `glib_genmarshal`, and `gobject_query` when Meson's GNOME module needs them.
- Generate Python wrappers for GLib helper scripts using `sys.executable` when the helper
  script shebang is not reliable.
- Add dependency `bin/` directories to `PATH` and dependency library directories to the run
  environment during build/test.
- On OHOS, add the selected GLib package's `libintl.so` or `libintl.a` to Meson C link args
  when `g_libintl_*` symbols are unresolved.
- Create `libfoo.so` and soname aliases after build/package; use `os.symlink()` first and
  `shutil.copy2()` as fallback.
- Sign installed `.so` and `.so.*` files with `binary-sign-tool` in `package()` for OHOS.

## Patch Guidance

Keep source patches narrow. For ATK 2.28.0, the source patch only:

- changes Meson project version from `2.28` to `2.28.0`;
- extends the Linux linker flag check to `harmonyos`.

Avoid adding a package-specific `intl-wrapper.c` until recipe-side linking to the GLib
package's `libintl` has been tested and ruled out.

## Verification Expectations

- W0 dependency check should prove the selected GLib package exists in the registry.
- Upstream Meson tests should remain enabled and run when `can_run()` is true.
- `test_package` should compile and execute a C/CMake consumer that includes public headers
  and calls real API symbols.
- For ATK, the reference `test_package` includes `<atk/atk.h>`, checks version helpers, and
  resolves core `GType` values.
