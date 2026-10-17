# Draft: raw Makefile Conan recipe — make -C {source_folder} + env CPPFLAGS

> Source event: `libcyaml/1.4.2` first OHOS adaptation on 2026-09-03.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

`libcyaml` is a pure Makefile C11 project (no `configure` script). Adapting it
with the Conan Autotools template fails with two chained errors:

```text
make: *** No targets specified and no makefile found.
make: *** Makefile:165: build/release/shared/src/util.o] Error 1
src/util.c:50:6: error: use of undeclared identifier 'VERSION_MAJOR'
```

Root causes (two independent traps):

1. **Wrong build cwd**: Conan `basic_layout` runs `build()` from
   `build-release/`, but the upstream `Makefile` lives at the source root.
   → `make -C {self.source_folder}` fixes it.
2. **CLI CPPFLAGS overrides `+=`**: the upstream Makefile composes
   `CPPFLAGS += $(VERSION_FLAGS)`. Passing `CPPFLAGS=...` on the make command
   line suppresses the `+=`, dropping `-DVERSION_MAJOR/MINOR/PATCH`.
   → prefix the flags on the invocation as **environment** variables
   (`CPPFLAGS='-I<dep>/include' LDFLAGS='-L<dep>/lib -l<dep>' make ...`),
   which GNU make appends via `+=`.

## Recommended recipe shape

```python
def build(self):
    apply_conandata_patches(self)
    libyaml = self.dependencies["libyaml"]
    inc = os.path.join(libyaml.package_folder, libyaml.cpp_info.includedirs[0])
    libd = os.path.join(libyaml.package_folder, libyaml.cpp_info.libdirs[0])
    self.run(
        f"CPPFLAGS='-I{inc}' LDFLAGS='-L{libd} -lyaml' "
        f"make -C {self.source_folder} VARIANT=release CC=clang AR=llvm-ar")

def package(self):
    build_dir = os.path.join(self.source_folder, "build/release")
    copy(self, "cyaml/*.h", os.path.join(self.source_folder, "include"),
         os.path.join(self.package_folder, "include"))
    copy(self, "libcyaml.a", build_dir, os.path.join(self.package_folder, "lib"))
    copy(self, "libcyaml.pc", build_dir, os.path.join(self.package_folder, "lib/pkgconfig"))
```

## Related

- `E097` covers "no configure, custom Makefile" identification only (BearSSL);
  this draft adds the Conan-recipe injection technique (new diff).
- `E074` covers the make jobserver FIFO restriction: do not use `-j$(nproc)`
  on HMDFS-class filesystems (`make: jobserver mkfifo: Operation not permitted`);
  use serial `make`.

## Validation

`ohc-run.py conan-verify libcyaml 1.4.2` → G1–G4 PASS, `test_package` 2/2 passed
(consumer test + OHOS-specific UTF-8 round trip).
