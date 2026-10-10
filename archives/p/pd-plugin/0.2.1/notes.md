# pd-plugin 0.2.1 — HarmonyOS PC adaptation notes

## Software and source

`plugin~` is a Pure Data external that searches for, loads and runs LADSPA
audio plugins. The authoritative release is the official SourceForge archive:

```text
https://sourceforge.net/projects/pure-data/files/libraries/plugin~/plugin~-0.2.1.tar.gz/download
sha256: 3135ef0bfc2e42976104ad1dbd0b8e9e2d6db4caa74a63814636373ab957d928
```

The archive contains 13 top-level files, including three C sources. It has no
test directory, test source or `test`/`check` build target, so the upstream
test inventory is 0 tests (0 run, 0 passed, 0 failed).

## Build and dependencies

The published dependencies were checked before implementation:

- `puredata/0.54.1` supplies `m_pd.h`.
- `ladspa-sdk/1.17` supplies `ladspa.h` and the runtime ABI.

The upstream Makefile hard-codes traditional system include directories and
host assumptions. The recipe therefore performs the same three-source build
directly with the C compiler selected by Conan's
`tools.build:compiler_executables` profile setting:

```text
clang -std=gnu11 -fPIC -O2 -DPD -DUNIX -DHAVE_LOCALE_H ... -c plugin~.c
clang -std=gnu11 -fPIC -O2 ... -c jload.c
clang -std=gnu11 -fPIC -O2 ... -c jsearch.c
clang -shared -Wl,-soname,plugin~.pd_linux ... -ldl -lm
```

The result is installed at `lib/pd/extra/plugin~/plugin~.pd_linux` with its
three Pd patch files, README and ChangeLog. It is not a CLI and has no
`main()`, `bin/` output or `commands.json`; Pd loads the module with `dlopen`.
Its unresolved Pd symbols are intentional and are supplied by the running Pd
process.

## Source adaptation

`patches/0001-plugin~.c.patch` replaces 17 uses of the removed legacy
`error(format, ...)` API with `pd_error(x, format, ...)`. Current Pure Data
0.54.1 declares `pd_error()` but not `error()`. Passing the owning `plugin~`
object preserves the diagnostic and lets Pd associate it with the object.
No HarmonyOS-only preprocessor branch is introduced.

## Tests

The adaptation adds one HarmonyOS-specific runtime consumer test containing
20 checks. `pd_plugin_test.c` exports the minimal Pd ABI that a real
`-rdynamic` Pd executable supplies, then:

1. loads the packaged OHOS aarch64 external with `RTLD_NOW | RTLD_GLOBAL`;
2. resolves the setup entry and all four LADSPA helper entry points;
3. calls `plugin_tilde_setup()` and verifies one class plus eight methods;
4. searches the real `ladspa-sdk` plugin directory;
5. loads `amp.so`, resolves `amp_mono`, instantiates it and processes four
   audio samples with gain 2;
6. verifies the exact output samples and cleanly unloads the libraries.

Thus adapted test count is 1, strictly not less than the upstream count 0,
and all 20 assertions execute real packaged code rather than checking only
for file existence.

## Verification

The required verification command is:

```bash
conan create archives/p/pd-plugin/0.2.1 \
  --name=pd-plugin --version=0.2.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=pd-plugin/*
```

Success requires the recipe build, packaging and test_package executable to
complete with `20 checks, 0 failures` on HarmonyOS PC aarch64.

## Final status

COMPLETED — the HarmonyOS PC aarch64 Conan build, package test and
CI-equivalent quality pipeline all passed.
