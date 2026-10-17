# wmtop

wmtop is a Window Maker dock application that continuously displays the
processes consuming the most CPU (and, on Linux-family kernels, memory) in a
small window. It is a monitoring tool for the Window Maker / dockapps
ecosystem, built on top of libdockapp and the X11 toolchain.

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 0.85 | published | First OHOS PC adaptation; conan-verify G0-G4 PASS |

## OHOS PC adaptation summary

- Autotools bootstrap runs without `autoreconf`: on OHOS, scripts on HMDFS
  cannot be execve'd from conan's build tree, so `aclocal`/`automake` are
  invoked through the `perl` interpreter directly (explicit acdir arguments
  replicate the packaged wrapper semantics) and `configure` is executed via
  `sh`.
- The upstream tarball declares no `TESTS`/`check_PROGRAMS`; `make check`
  runs and completes with zero cases (recorded in `0.85/notes.md` and
  `0.85/test_package/MANIFEST.yml`).
- The consumer test package drives the installed binary end-to-end, including
  one HarmonyOS-specific executed use-case (runtime shared-library chain
  resolution up to libdockapp's X11 initialisation).

## Usage

```sh
conan install --requires=wmtop/0.85@ohpcd/stable -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
wmtop -v          # wmtop v0.85
wmtop -Z          # usage banner (lists the LINUX-only -m memory view)
```
