# libxext 1.3.7 W0 report

Date: 2026-08-20 (Asia/Hong_Kong)

## Result

`PASS`

The exact current-main candidate resolves every dependency from `ohpcd` in a
fresh isolated OHOS/arm64 Conan home with `--build=never`. No source fallback
was allowed.

## Bound inputs

- Candidate HEAD and repository base are recorded in the external
  `w0-summary.json`; they are intentionally not duplicated in this staged
  report because the final metadata commit changes the candidate identity.
- Create-new durable evidence:
  `E:\HarmonyPC\validation\libxext-1.3.7\w0-current-main-20260820-r30`.
- The exact staged candidate tree is recorded in that evidence's
  `w0-summary.json`; it is intentionally not duplicated here because this
  report is itself a staged candidate member.
- Host/build profile: OHOS 6.0, armv8, clang 15, Release.
- Conan client: community OHOS-adapted Conan 2.29.1.
- Remote: `ohpcd` at
  `https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/`.
- Resolution policy: `--build=never` in a fresh task-isolated Conan home under
  `F:\HarmonyPC`; `conancenter` is disabled and Conan package downloads are
  limited to one thread.

The exact lowercase target `libxext/1.3.7` is not already published: a fresh
recipe download and OHOS binary install both returned `Unable to find`, and a
builder-2 history scan found zero exact `archives/l/libxext/1.3.7` release
builds. The historical `archives/l/libXext/6.4.0` release attempts both failed
and used the upstream SONAME as the package version, so they are not a newer
upstream release or a published predecessor for repair-version purposes.

## Version authority reconciliation

The official X.Org archive index returned HTTP 200 on 2026-08-20 and lists
`libXext-1.3.7.tar.xz` as the highest stable release. It contains no
`libXext-1.7.0.tar.xz`; the captured index and parsed version inventory are at
`E:\HarmonyPC\validation\libxext-1.3.7\upstream-authority-20260820-r1`.

The software manifest retains the old `1.7.0` status as a historical
publication fact, but marks its upstream identity invalid and excludes it from
supersession. The row has no matching version directory, source URL, or
SHA256; historical `6.4.0/notes.md` records that the old attempt used a moving
master archive with an empty SHA256. It is therefore not a newer upstream
version even if the ref was once published. A fresh isolated Conan readback at
`E:\HarmonyPC\validation\libxext-1.3.7\version-authority-20260820-r1`
resolved the known historical `libxext/6.4.0` recipe, while `1.7.0` returned
RC 1 with the registry's `system acceleration policy not enabled` error. That
ambiguous error is not used as absence proof or to erase the publication
record. Official upstream/source authority only establishes that `1.7.0` is
invalid lineage and cannot supersede stable `1.3.7`.

## Direct dependencies

### libx11/1.8.13

- RREV: `e3ce69008a37ca95d1f0918c47709057`
- Package ID: `cae7d429fb6839b6840b7602f11bf20c76efecdf`
- PREV: `701e81816807aea0ad862a324557f4e9`
- Binary state: `Download`
- Binary remote: `ohpcd`
- `info_invalid`: empty

### xorgproto/2025.1

- RREV: `f5274e33759da898a6e8d87d7708d47c`
- Package ID: `283a988d63e011a731408b6abe0950de49e6171d`
- PREV: `b7dc443b533634631c412ae235a57198`
- Binary state: `Download`
- Binary remote: `ohpcd`
- `info_invalid`: empty

## Resume condition

The provider-publication gate is clear. Proceed to one exact-snapshot W3
through the official finish flow, then perform a fresh independent W4 before
push or submission. This W0 does not itself claim W3, finish, W4, CI, review,
publication, or submission completion.
