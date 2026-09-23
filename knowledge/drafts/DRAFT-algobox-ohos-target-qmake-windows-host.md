# Draft: OHOS-target qmake binaries cannot run as Windows host tools

> Status: DRAFT | Created: 2026-08-28 | Related package: algobox 1.1.1

## Symptom

Windows-host validation can resolve the Conan graph for `algobox/1.1.1`, but the build stops when it tries to execute `qmake6` from the OHOS-target `qtbase/6.11.1` package:

```text
OSError: [WinError 193] %1 is not a valid Win32 application
```

## Root cause

The dependency package exports a target-built `qmake6`, not a Windows host tool. Graph resolution succeeds because the package exists, but the binary itself is not runnable on the host that is trying to drive the build.

## Fix

Keep Windows-host work to:

1. source inspection
2. dependency graph resolution
3. metadata validation

Then move the full `qmake` build to an OHOS-compatible runner, or switch to a host-native Qt toolchain if one is available for the same workflow.

## Validation

For `algobox 1.1.1`, `conan graph info` passes with the temporary cache, but direct `subprocess.run([qmake6, "-v"])` fails on Windows with WinError 193. That is the expected boundary: the package exists, the tool is not host-runnable.

Patch files handed to Conan must stay as literal unified diffs. If CI reports a patch parse error, validate the patch text itself with `git apply --check` against an extracted source tree before rerunning the build.

For this package, the patch chain applies in order on the upstream tarball: `0001` -> `0002` -> `0003`.

On OHOS CI, `qtcore5compat/6.11.1` may still define the module but not expose a usable `QTextCodec` header. For AlgoBox, keep the Qt 5 path on `QtCore/QTextCodec`; on Qt 6 include a local shim that first tries available compatibility headers, then falls back to `QStringDecoder`/`QStringEncoder` for UTF-8 and Latin-1 conversions.

When replacing a `QWebEngineView` flow with a `QTextBrowser` fallback, also remove vestigial `QWebChannel` C++ includes, registration calls, and qmake modules. Keeping those hooks after JavaScript execution becomes a no-op can make CI probe or include a Qt module that the fallback no longer uses.

If the fallback only needs text conversions, keep the compatibility layer fully local instead of probing `QtCore5Compat` first. That avoids dragging in an unavailable shared library while still preserving `QTextCodec`-style call sites.

If `qmake` reports `Unknown module(s) in QT: core5compat`, remove the module from the `.pro` file and let the local shim provide the API surface instead of forcing the recipe to discover a missing Qt module.

When a patch adds C++ string literals such as `"\n"`, keep the backslash escaped in the patch text and validate the applied source. A literal newline inside the generated C++ string causes `expected expression` and follow-on brace errors that look unrelated to the original fallback change.

## Notes

This draft is reusable for other qmake-based Qt packages that resolve fine but cannot drive a full build from a Windows host.
