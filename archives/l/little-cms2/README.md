# Little CMS 2

Little CMS 2 is Marti Maria's ICC **colour management engine**: it reads and
writes ICC profiles, builds colour transforms between them and performs the
rendering-intent work in between.  It is what most image pipelines, PDF
renderers and print workflows on a POSIX system link against for colour.

- Upstream: https://github.com/mm2/Little-CMS
- Release: 2.19 (tag `lcms2.19`)
- License: MIT
- Build system: autotools (the release tarball ships a generated `configure`)
- Package form: `lib/liblcms2.a` + `include/lcms2.h` / `lcms2_plugin.h`, plus
  the command-line utilities `linkicc`, `transicc` and `psicc`

## Configuration

```
--disable-shared --enable-static
--without-jpeg --without-tiff     # skips the jpgicc / tificc utilities
--without-zlib                    # no ICC profile compression
```

The two omitted utilities are the only parts of lcms2 that need third-party
libraries; leaving them out keeps the package dependency-free.  The library,
the complete test suite and the remaining three tools are unaffected.

## HarmonyOS PC adaptation

Three portability patches against the generated autotools platform scripts;
the engine itself is untouched.

| Patch | Purpose |
|---|---|
| `0001-config.guess.patch` | teach the shipped 2018-02-24 config.guess the `aarch64-unknown-linux-ohos` triple (`__OHOS__` libc probe, placed before the unconditional `<features.h>` include, plus the `*:HarmonyOS:*:*` uname case) |
| `0002-config.sub.patch` | accept `ohos-linux` / `linux-ohos` as a valid cpu-os-kernel combination |
| `0003-configure.patch` | create the private `config.status` temp directory with `umask 022` instead of `077` (OHOS HMDFS makes the `077` directory unusable) |

## Upstream tests

`testbed/` builds `testcms` from three sources and registers **163** checks that
cover profile I/O, colour-space conversion, the plugin system, multilingual
tags and the internal memory debugger.  They run for real inside `build()`:

```
./testcms --exhaustive
```

`--exhaustive` matters: six of the registered cases (the slow exhaustive 1D/3D
interpolation sweeps) sit behind that runtime switch and the default run
executes only 157.  The recipe passes the switch so the full registered set is
covered, and reports the measured counts rather than declaring them.

See `2.19/notes.md` and `2.19/test_package/MANIFEST.yml` for the full record.
