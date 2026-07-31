# xtrans 1.6.0 W0 dependency report

## Scope

- Dependency Issue: `#1291` (`【依赖项】xtrans 1.6.0`).
- Downstream tasks: OpenJ9 `#1084` and GraalVM `#1085`.
- Initial check: `2026-07-19 12:46 +08:00`.
- Final target recheck: `2026-07-25`.

## Contest and duplicate checks

- The contest repository list returned `Total 0` for `xtrans`.
- The complete GitCode Issue list returned no same-name `xtrans` Issue before
  the dependency Issue was created.
- xtrans is outside the contest task list, so only the dependency Issue was
  created; no contest claim Issue was created.

## Dependency metadata

The official Homebrew formula metadata identifies xtrans 1.6.0 with no runtime
dependencies. Its listed `pkgconf` and `util-macros` inputs are build tools, not
Conan libraries exported to consumers.

The final recipe has one real third-party Conan requirement:
`xorgproto/2025.1`. It supplies public headers included by the installed xtrans
sources. Publication was required before formal W3 and is confirmed below.

## Conan remote evidence

Checks used an isolated Conan home and the configured `ohpcd` remote.

```text
conan download zlib/1.3.1 -r=ohpcd --only-recipe
exit=0

conan download xtrans/1.6.0 -r=ohpcd --only-recipe
exit=1
ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]

conan install --requires=xtrans/1.6.0 -r=ohpcd --build=never
exit=1
Unable to find 'xtrans/1.6.0' in remotes
```

The independent graph-resolution result establishes that xtrans 1.6.0 is not
published despite the remote acceleration-policy message. No
`--build=missing` fallback was used for this W0 conclusion.

## Prerequisite publication recheck

Fresh HarmonyOS/AArch64 W3 r15 rechecked `xorgproto/2025.1` with an isolated
Conan home. Conan downloaded both the recipe and the required OHOS/armv8 binary
from `ohpcd`; it did not build the prerequisite from source:

```text
xorgproto/2025.1#f5274e33759da898a6e8d87d7708d47c
package_id=283a988d63e011a731408b6abe0950de49e6171d
binary_revision=b7dc443b533634631c412ae235a57198
Install finished successfully
```

This supersedes the earlier unpublished checkpoint. The frozen recipe and
binary logs are included in r15 evidence and covered by the evidence manifest.

## Conclusion

xtrans 1.6.0 is a new dependency package. Its xorgproto prerequisite is now
consumable from `ohpcd`. Fresh target W3 r15 produced an immutable 73-row
terminal ledger with zero unexpected terminals; independent classification
identifies 4/4 substantive workflows, 69 uncounted build preflights, and 134
uncounted verification observations. The historical ledger remains unchanged,
and the dependency-publication block is closed.

## Knowledge submission boundary

The reusable test method identified during adaptation is carried as the paired
E234 knowledge draft with the xtrans software submission. Path A+B remains the
applicable classification; this dependency PR does not modify the formal
knowledge graph, document set, index, or `SUMMARY.md`.
