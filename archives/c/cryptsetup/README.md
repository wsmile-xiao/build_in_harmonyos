# cryptsetup

`cryptsetup` is the reference toolset and `libcryptsetup` library for LUKS
(Linux Unified Key Setup) disk encryption — LUKS1/LUKS2 container formatting,
unlocking, reencryption, plus `veritysetup` (dm-verity) and `integritysetup`
(dm-integrity) utilities.

## Versions

| Version | Status |
| --- | --- |
| 2.8.8 | built |

Homepage: https://gitlab.com/cryptsetup/cryptsetup

## OHOS adaptation notes

- Crypto backend: openssl (OHOS has no kernel crypto API userland access).
- `--disable-udev --disable-selinux --disable-nls --disable-ssh-token`:
  udev/systemd, libselinux, gettext and argp are absent on OHOS.
- Test suite: file-based LUKS2 lifecycle works without root/dm-crypt;
  dm-backed cases are environment-bound (see 2.8.8/notes.md).
