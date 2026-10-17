# libslirp 4.9.3 adaptation notes

## Scope

- Downstream: DOSBox Staging issue `#1093`.
- Official source: tag `v4.9.3`, release commit
  `dd76415fce457e319d665eb8210d05c5731360ba`.
- Official archive SHA-256:
  `ee698ca4ce05217ca7d520c7f0b1b1228fd7d32922dd32d1051c347152588417`.
- Version selection: latest stable upstream release. DOSBox Staging 0.82.2
  enables slirp by default and accepts `>=4.6.1,<5`.
- W0 dependency: `glib/2.84.0`, recipe revision
  `f67d99412319fab1849399b3878a424c`.

## Dependency topology

```text
DOSBox Staging 0.82.2-r1
`- libslirp 4.9.3
   `- glib 2.84.0
      |- libffi 3.4.4
      `- pcre2 10.40
```

Upstream `meson.build` has one unconditional normal-platform third-party
dependency, `glib-2.0`. Windows-only `iconv`, `ws2_32`, and `iphlpapi` are not
additional OHOS Conan dependencies.

## Version migration

The existing Issue `#1640` is retained. The closed PR `#3737` is historical;
the current submission is PR `#3786`. Version 4.9.3 replaces the unpublished
4.9.1 adaptation because it is the latest stable release within DOSBox's
supported major-version range. The public `src/libslirp.h` is byte-identical
between 4.9.1 and 4.9.3. The intervening releases contain security and defect
fixes without a public API change.

No 4.9.1 build or test evidence is counted for this version. All 4.9.3 build,
upstream-test, consumer, W4, review, and CI results are from fresh runs.

## Build adaptation

The recipe maps Conan's `shared` option to Meson's `default_library`. A static
package also enables upstream's `static` option so the GLib dependency is
resolved statically. Network access from Meson wraps is disabled.

GLib is a public Conan link requirement. The recipe marks its headers and
libraries transitive and declares `glib::glib` in `cpp_info.requires`, so
downstream consumers retain the required link contract.

On OHOS/HarmonyOS the portability patch uses `meson.project_version()` instead
of directly executing `build-aux/git-version-gen` from HMDFS. It also omits
upstream's versioned shared-library declaration so installation produces one
real `libslirp.so`, not a versioned file plus symbolic links. Other platforms
retain upstream behavior.

When target execution is possible, the recipe signs `libslirp.so`, `pingtest`,
and `ncsitest` before Meson tests. The installed shared library and consumer
must each contain exactly one `.codesign` section.

## Test accounting

Version 4.9.3 registers two independent Meson integration tests, `ping` and
`ncsi`. The installed-package consumer is one additional integration flow. It
checks the runtime version, initializes a real `Slirp` context, exercises state
and poll APIs, verifies callback cleanup, and exits nonzero on any failure.

Repeated shared/static builds, signing checks, and internal assertions are not
counted as additional test cases.

## Current evidence boundary

- W0: PASS for `glib/2.84.0` recipe availability.
- Official v4.9.3 upstream tests: PASS `2/2`; both fresh executions used the
  unmodified upstream `ping` and `ncsi` test registrations.
- Fresh fallback-device `finish` r3: G2 and embedded W3 each completed a
  real `conan create`; upstream tests passed `2/2`, the installed-package
  consumer passed `1/1`, and the skill generated `.ci-result.json` with exit
  code 0 and integrity value `9d52fd260fb65860`.
- Fresh primary-device r4: the standard `build_and_test.sh` pipeline returned
  0; L0, L1 (including the destructive reverse test), L4, and L5 passed;
  upstream tests passed `2/2` and the consumer passed `1/1`.
- Both devices produced the same 1,038,912-byte AArch64 shared object with
  SHA-256
  `eeceed68e1637b31da93899a0c5048f8d5ca4b1d9a021c34698e6db2fc47acc7`.
  Each package contains one real `libslirp.so`, no library symlink, and one
  `.codesign` section.
- Frozen evidence bundle SHA-256 values are
  `34254c2ede3bacd9100c4e69238515da54d5ecd463d24ae293ad298274107664`
  (fallback r3) and
  `fa70010e0f983d31b96b567c4bde91d88c466e5caf4a2f044d753de8ed842d3a`
  (primary r4).
- The fallback `finish` outer process returned 1 only after G2 and W3 passed,
  because the historical close/readiness path still requests deprecated
  `packaging/` and `.staging-verified` artifacts and evaluates a reduced
  snapshot as a full repository graph. Those artifacts were not fabricated.
- W4: PASS for frozen input HEAD
  `0502bd41545d4e97d4aeaa35d400736a3accf662`; P0=0, P1=0, P2=1, P3=0.
  The non-blocking P2 records use of an upstream deprecated compatibility API
  in the already validated consumer.
- PR `#3786` HEAD `98e95187f7374ea01459031444fa891f14b39354`
  passed official CI build `#12131` (`ci?id=12871`). Publication remains a
  post-merge release step and is not implied by PR validation.
