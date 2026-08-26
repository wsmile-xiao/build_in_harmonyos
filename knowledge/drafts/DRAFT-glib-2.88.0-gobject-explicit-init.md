# DRAFT-glib-2.88.0-gobject-explicit-init: HarmonyOS native GObject explicit initialization

> Contributor: glib 2.88.0 adaptation | Status: Draft | Updated: 2026-08-25
> Source: archives/g/glib/2.88.0

## Symptom

A GLib consumer can pass simple `glib` core checks, but still be under-tested
if the smoke test never touches GObject or GIO. On HarmonyOS native runs, the
first real use of the GObject type system should not assume that GLib's ELF
constructor path has already initialized every type-system global.

The glib 2.88.0 adaptation therefore tests a path that consumes:

- `glib`: strings, hash tables, variants
- `gobject`: explicit type-system initialization and `G_TYPE_OBJECT`
- `gio`: `GFile`

The passing test output was:

```text
test glib 2.88.0: OK (string/hashtable/variant/gobject/gio)
```

## Root Cause

Upstream GLib/GObject normally initializes the type system through a library
constructor. That is fine on platforms where ELF `.init_array` constructors are
reliably run before first GObject use.

HarmonyOS native Conan jobs are a different enough runtime surface that the
glib adaptation should provide an explicit initialization escape hatch instead
of depending entirely on the constructor side effect. The 2.88.0 patch adds:

```c
void g_type_ensure_initialized (void);
```

The implementation uses `g_once_init_enter()` / `g_once_init_leave()` and calls
`gobject_init()` only if the type system has not already been initialized.
This keeps the API safe when called repeatedly or after the constructor has
already run.

## Adaptation Pattern

In a GLib package or downstream smoke test that intentionally validates
GObject/GIO consumption on HarmonyOS, call the explicit initializer before the
first object construction:

```c
g_type_ensure_initialized();
g_type_ensure_initialized();

GObject *o = g_object_new(G_TYPE_OBJECT, NULL);
g_assert(G_IS_OBJECT(o));

GFile *f = g_file_new_for_path("/tmp/glib-test-file");
g_assert(G_IS_FILE(f));
```

Calling it twice is deliberate test coverage: the function must be idempotent.

## Verification

Authoritative device run:

```text
run_id=codex-glib-glib-2.88.0-C0DX-r1-shadow-ci-r7-20260825-203338-6764
command='zsh' 'ci/conan/build_and_test.sh' 'archives/g/glib/2.88.0'
exit_code=0
```

Observed result:

- L0/L1/L2/L4/L5 passed.
- Upstream Meson tests: 302 ok, 0 failed, 6 skipped.
- `test_package` ran the GLib/GObject/GIO smoke test above.
- L1e destructive negative test moved `bin/` and `lib/` away and confirmed the
  smoke test genuinely depends on glib package artifacts.
- Build Summary: Total 1, Success 1, Failed 0.

## Non-Goals

This is not the same issue as:

- `gobject-2.0.pc` forwarding for consumers using Meson `dependency()`.
