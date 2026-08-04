# E253 - Static C API archive omits its C++ runtime from pkg-config

## Error signature

A static library builds successfully and exposes a C API, but a pure C
consumer linked through `pkg-config --static` fails with C++ runtime symbols:

```text
undefined symbol: std::__n1::this_thread::sleep_for(...)
undefined symbol: operator new(unsigned long)
undefined symbol: __cxa_begin_catch
```

## Trigger conditions

- The package installs a static archive and an upstream `.pc` file.
- One selected implementation backend compiles C++ objects into that archive.
- The downstream source is C and therefore uses the C linker driver.
- `Libs.private` does not name the selected C++ runtime.

## Root cause

The public language of an API does not determine the implementation language
of every object in a static archive. Shared libraries record their own runtime
dependencies, while static consumers must receive every private dependency at
their final link. Conan `cpp_info.system_libs` helps Conan-generated consumers
but does not alter a separate upstream pkg-config file installed by the recipe.

## Recommended fix

Add the selected C++ runtime and the archive's other private system libraries
to the installed `.pc` `Libs.private` field for static packages. Keep the
Conan metadata consistent with the installed pkg-config metadata. Prefer an
upstream-supported generation variable when one exists; otherwise perform a
strict package-time edit that requires exactly one `Libs.private` field.

For HarmonyOS libc++ builds, the validated FluidSynth list is:

```text
Libs.private: -lm -lpthread -lc++
```

## Forbidden shortcuts

- Do not rename the C consumer to C++ or force `LINKER_LANGUAGE CXX`; that
  hides the installed metadata defect.
- Do not add `-lc++` only to the test command.
- Do not rely only on `cpp_info.system_libs` when the package also promises an
  installed pkg-config interface.

## Validation

1. Check that `pkg-config --static --libs` contains the expected private flags.
2. Compile and run an unchanged pure C installed-package consumer.
3. Rebuild the shared configuration to prove the static-only metadata change
   does not affect shared consumers.
4. Bind both terminal runs to the same recipe manifest.

FluidSynth 2.5.7 on HarmonyOS/aarch64 validated this pattern with 30/30
upstream tests and 3/3 installed-package consumers in both shared and static
configurations.
