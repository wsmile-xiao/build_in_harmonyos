# libevent 2.1.13 adaptation notes

## Build decisions

- Use upstream CMake rather than carrying the five legacy 2.1.12 Autotools patches.
- Build one Conan-selected library type through `EVENT__LIBRARY_TYPE`.
- Keep the official regress and peripheral tests enabled; disable only samples,
  benchmarks, and optional OpenSSL support.
- Add `zlib/1.3.1.1` as a test requirement so the zlib regress case is compiled
  and executed without becoming a runtime dependency of the package.

## HarmonyOS behavior

- `CMAKE_SYSTEM_NAME=HarmonyOS` emits real unversioned `.so` files and skips
  upstream's extra symlink command. The recipe supplies CMake's missing
  SONAME/runtime linker flag contract for the platform.
- Upstream's CTest dumpevents command encodes `|` as a literal argument. The
  recipe excludes those registrations, reads their structured CTest
  environments, and passes producer stdout to the Python checker directly.
- Native HarmonyOS execution signs build-tree tests, shared libraries, and
  consumer executables before running them.
- HarmonyOS headers define `POLLRDHUP`, but the native `poll()` backend does
  not deliver the half-close event semantics that libevent associates with
  that constant. Patch 0002 disables `EV_FEATURE_EARLY_CLOSE` for the OHOS
  poll backend without changing tests or any other platform.
- The native `epoll()` backend has the same `EPOLLRDHUP` capability gap.
  Patch 0003 uses the probed feature value both in the event mask and the
  advertised backend feature set.
- Patch 0004 backports upstream commit
  `c257e16f5bf48ad947b00f4eb59ace34f9b136d1`, allowing the test-only lock
  tracer to recognize allocator address reuse without false lock errors.
- Patch 0005 backports `TMPDIR` behavior from upstream commit
  `f6c9f9ae8af978fc578c291d00a74cf99640342b` and the required `PATH_MAX`
  include from `6c0d7ec6e8863d5abeaf6e842ee7a9e7c0526250`. The recipe creates and
  exports its own writable test directory.
- Patch 0006 preserves the DNS API contract under descriptor exhaustion.
  HarmonyOS resolves `localhost` from a built-in mapping, then the connection
  socket fails with `EMFILE`; the test keeps `BEV_EVENT_ERROR` and explicitly
  requires `dns_error == 0` instead of dropping the assertion.

## Upstream test result

- The official upstream CTest suite passed `49/49`.

Final clean recipe log SHA256:
`375e793e8c9cb89e35d9e8d2c42c51e3756392d98f65e82645ac2af0f04d630f`.

## Recipe closure status

- The frozen execution tree
  `362cad634f1f34dc82b4cf18e915a6d38c7ee5c5` was packaged as canonical
  candidate SHA256
  `a9aae71f1f362638ff287fae1d50a9e51999875138d7eddfba43c25892fb5c5e`.
- All six declared patches replay against the official archive through both
  Git on LF-normalized inputs and Conan's `patch-ng` backend with
  `fuzz=False`. The resulting 221-file source trees are byte-identical, and
  the six patched target-semantic post-images are LF-only.
- A fresh `conan create` completed successfully from the frozen candidate;
  dependency resolution, package creation, and installed-package consumers
  all completed without error.

## Supporting recipe checks

- The generated configuration contains `#define EVENT__HAVE_LIBZ 1`, and
  `bufferevent/bufferevent_zlib` is a runnable regress entry.
- Component-level runtime `bindirs` are required because Conan aggregates
  component metadata for `VirtualRunEnv`. The regenerated run environment now
  includes both the package `bin` and `lib` directories, and every consumer has
  a 60-second CTest timeout.
