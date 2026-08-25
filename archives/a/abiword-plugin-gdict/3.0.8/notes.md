# abiword-plugin-gdict 3.0.8 adaptation notes

## Worktree

- Branch: `feat/abiword-plugin-gdict-3.0.8`
- Worktree: `D:\harmonyos\worktrees\abiword-plugin-gdict-3.0.8-pr`
- Upstream: `https://gitlab.gnome.org/World/AbiWord`
- Release: `release-3.0.8`
- Source SHA256: `7c490e46f0a6143f84d5c7e3fed246f34486ad70cd55f162c792827607cd7e9a`

## Current status

W0-W3 preparation and OHOS shadow validation are complete. The recipe builds
only `plugins/gdict` from the AbiWord 3.0.8 source tree. All direct Conan
dependencies resolved in shadow r20: `boost/1.90.0.3`, `glib/2.84.0.1.1`,
`libgsf/1.14.58`, `wv/1.2.9`, `libxslt/1.1.45.2`, and
`libxml2/2.15.3.1`. AbiWord itself is intentionally not a Conan build
requirement; the host ABI symbols are resolved by AbiWord when the module is
loaded.

The GitLab source archive does not contain generated Autotools files. The
recipe exports the required `m4/` macros and runs aclocal, autoconf,
autoheader, libtoolize, and automake in the Conan build environment before
configuring and building only `plugins/gdict`.

## W0 result

The r20 dependency graph resolved all direct and transitive packages on the
OHOS worker, including the separately adapted GLib and wv packages restored
from their dedicated caches.

The shadow run built and packaged `gdict.so`, executed the package smoke test,
and reported `5 passed, 0 failed`. The runner completed with `rc=0`; no
dependency publication blocker remains for this recipe.

## Source and test analysis

- Build system: Autotools; the archive has no generated `configure` or
  `Makefile.in`.
- The recipe supplies the required Autoconf macros and tool data, then creates
  a plugin-only out-of-tree build.
- The gdict plugin is a UNIX/GTK module using `fork/execvp` to invoke
  `gnome-dictionary` at runtime.
- The standalone OHOS path disables GTK headers because gdict's runtime launch
  path does not call GTK APIs.
- FriBidi and GLib require nested generated-header include directories during
  the plugin compile.
- `gdict.so` intentionally retains the AbiWord host ABI references for
  resolution by the host process at `dlopen` time.
- There is no gdict-specific upstream test target. `test_package/test_gdict.sh`
  checks that the packaged module is an ELF shared object and exports the three
  AbiWord plugin ABI symbols: `abi_plugin_register`,
  `abi_plugin_unregister`, and `abi_plugin_supports_version`.
- Full `make check` remains a host/UI AbiWord test suite and is not run by this
  standalone plugin package.

## Shadow CI validation

- Device: `10.62.221.191:2222`
- Run: `codex-gdict-r20-abiword-plugin-gdict-abiword-plugin-gdict-3.0.8-shadow-r20-20260822-033547-4513`
- Official lock wait: `0s`; runner result: `rc=0`
- Package: `abiword-plugin-gdict/3.0.8#4b38fa7fa081ded08358c23bc5e8870b:245617bc1bd66d4b772e9e617b0ba93fc2d093a5#bddbd8c63b16a74061a1c99e02a46eb1`
- Layers: L0/L1/L4/L5 passed; L2 skipped because the package has no `bin/`
- Cache: `/storage/Users/currentUser/ohos-users/codex-abiword-plugin-gdict-3.0.8-r20-cache.tgz`
- Cache SHA256: `d04876bb52e7b83efdbf7e98f79ff3f5e3357b8180affc824f6fcdf0721e6d90` (11,585,221 bytes)

Next shadow CI command, still queued as a single heavy package through the
official device runner:

```sh
CI_PACKAGES="archives/a/abiword-plugin-gdict/3.0.8" \
  zsh ci/conan/build_and_test.sh archives/a/abiword-plugin-gdict/3.0.8
```

## Remaining scope

No adaptation blocker remains. Loading the plugin inside a complete AbiWord
process and launching `gnome-dictionary` are application-integration checks;
the package test deliberately covers the standalone ELF and plugin ABI contract.

## Path B candidate

The reusable diagnosis and validation boundary for packaging a host-loaded
plugin without linking the host application are recorded in
`reports/path-b-candidate.md` and
`knowledge/drafts/E337-draft-abiword-plugin-host-abi-module.{kv,md}`. Final
Path B recognition remains subject to reviewer approval.
