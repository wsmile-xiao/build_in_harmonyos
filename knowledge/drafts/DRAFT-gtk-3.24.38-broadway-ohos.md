# DRAFT-gtk-3.24.38-broadway-ohos - Broadway build and no-display consumer validation

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-27
> **Severity**: high | **Category**: meson / GTK / OHOS filesystem

## Scope

Use this entry when building GTK 3.24 on HarmonyOS PC where X11 and Wayland are
unavailable and build tools execute from HMDFS-backed paths.

## Implementation

Map upstream `GTK+` to the Conan-safe package slug `gtk`, enable Broadway, and
disable X11, Wayland, Quartz, Win32, introspection, demos, examples, and docs.
Use the pinned Conan GLib package's Python and compiled generator tools instead
of ambient PATH tools; pair them with the same dependency graph's library paths
to avoid shebang/module failures and `libffi.so.8` ABI leakage. Replace existing
pkg-config tool variables instead of only filling missing variables, because
generated `.pc` files can otherwise retain device-global absolute paths.
Copy compiled GLib tools into a GTK-private build directory and self-sign their
ELFs before Meson configure; continue to invoke GLib's Python generators through
the discovered interpreter. Embed resources through the portability patch so
optional external preprocessors are not required.

## Test boundary

The upstream GTK test registrations require a display server, input devices,
theme data, or the upstream GTK test harness. Those prerequisites are absent
from the headless HarmonyOS package runner, so the recipe does not build or
count them as passing. The deterministic consumer test links `gtk3::gtk3`,
validates runtime version 3.24.38, and resolves `GtkWindow` without opening a
display. It also passes the destructive dependency check after package headers
and libraries are moved away.

## Verification

Shadow CI completed all 889 Ninja steps, packaging, signed consumer execution,
R34 destructive dependency validation, and L0/L1/L4/L5. A hardware/display
enabled OHOS environment is required before claiming the upstream GUI test
matrix as executed.

## Source

- Package: `archives/g/gtk/3.24.38`
- Contrib task: `3718`
- PR: `build_in_harmonyos!6810`
