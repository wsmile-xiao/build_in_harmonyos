# DRAFT-zix-meson-build-tree-soname-alias - Meson shared-library aliases on OHOS

> Contributor: codex | Status: Draft | Updated: 2026-08-25

## Usage

Use this pattern when a Meson package builds a shared library on HarmonyOS PC,
but upstream tests or Conan consumers fail at runtime because the exact SONAME
filename is missing from the build or package directory.

## Symptom

zix 0.8.1 initially built successfully, then every executable linked against
the library failed during upstream `meson test`:

```text
Error loading shared library libzix-0.so.0
Error relocating ... zix_default_allocator: symbol not found
```

The test command already contained `LD_LIBRARY_PATH`, but the build tree only
contained the real versioned file:

```text
libzix-0.so.0.8.1
```

The loader searched for the binary's `NEEDED` entry, `libzix-0.so.0`, which did
not exist.

## Root Cause

Runtime search paths select directories, not alternate filenames. If Meson or
the target filesystem does not leave the SONAME alias next to the real shared
object, adding more paths does not help. The same issue can reappear after
`meson install` if the package `lib/` directory lacks either the SONAME alias or
the developer alias.

## Recommended Solution

After `meson.build()` and after `Meson.install()`, materialize the aliases in
the appropriate directory:

```python
for alias, target in (
    ("libzix-0.so.0", "libzix-0.so.0.8.1"),
    ("libzix-0.so", "libzix-0.so.0"),
):
    try:
        os.symlink(target, alias_path)
    except (OSError, NotImplementedError):
        shutil.copy2(versioned, alias_path)
```

Then run upstream `meson test` with the build directory in `LD_LIBRARY_PATH` and
run a real `test_package` consumer against the installed package.

## Verification

The final zix 0.8.1 shadow CI run passed with:

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content
```

Upstream Meson result:

```text
Ok:                21
Expected Fail:     3
Fail:              0
```

The Conan `test_package` ran `zix_consumer_api` and passed.

## Forbidden Approaches

- Do not rely on `LD_LIBRARY_PATH` alone when the SONAME filename is absent.
- Do not copy only the developer name and omit the SONAME alias.
- Do not skip upstream tests when the real issue is artifact layout.
