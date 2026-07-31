# mbrola-hu1 1.002 adaptation notes

## Source and version

The immutable source is Debian's `1.002+repack2` orig archive. The
competition version `1.002` maps to the voice database release declared by the
upstream README. The archive checksum is also recorded in Debian's signed
source metadata.

The recipe tries Huawei Cloud and Alibaba Cloud Debian mirrors before the
canonical Debian URL because the competition worker cannot reliably reach
`deb.debian.org`. All URLs serve the same 6,385,644-byte archive with SHA256
`9d972d76d6c8b72e010bfd44e4eaa5b8ef85e6e9dd92e95146c2f513d0854e35`.

The authoritative upstream voice directory is:

`https://github.com/numediart/MBROLA-voices/tree/master/data/hu1`

## License

HU1 uses a non-free, voice-specific MBROLA license. The database may be used
for speech synthesis only with MBROLA. It may not be sold or included in a
sold product without the voice owner's prior permission. Free redistribution
must include the original notice. The recipe therefore uses
`LicenseRef-MBROLA` and installs the unmodified `license.txt`.

## Packaging

This is architecture-independent voice data; no source compilation occurs.
The database is installed as `share/mbrola/hu1/hu1`. The upstream README and
the `kisk1` example are retained under `share/doc/mbrola-hu1`.

The package has no command of its own, so a software-level `commands.json`
would be incorrect. Consumers need a separately packaged MBROLA engine and can
locate the data through `MBROLA_VOICE_HU1`.

## Tests

Upstream documents one synthesis scenario:

```text
mbrola hu1 test/kisk1.pho kisk1.wav
```

Debian runs the same example as an autopkgtest. It is not executed by this
recipe because the MBROLA engine is a separate runtime and no Conan package
for that engine is available in this repository. This limitation is reported
as `not run`, not as a pass.

The deterministic validator still performs domain-level checks. It parses the
MBROLA binary header and all 1,596 diphone index records, verifies frame and
phoneme inventory invariants, parses the 598 segments in `kisk1.pho`, and
checks that all 597 requested adjacent phoneme transitions exist in HU1. It
also rejects a corrupt database header and malformed PHO pitch targets.

## Local validation

- Source semantic validation: passed, 18/18 assertions.
- Native Conan 2.29.1 `conan create`: passed, including the packaged consumer
  validation with 18/18 assertions.
- OHOS aarch64 profile: not run locally. The available standard Conan 2.29.1
  installation does not contain the competition toolchain's custom `OHOS`
  setting. The official competition CI remains the target-profile authority.
- MBROLA audio synthesis and HarmonyOS PC real-device validation: not run
  because neither the separately packaged engine nor a real device is
  available in this task.
