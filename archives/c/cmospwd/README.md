# CmosPwd

> CMOS/BIOS password recovery and backup tool.

## Intro

CmosPwd decrypts passwords stored in CMOS used to access BIOS SETUP. It covers
ACER/IBM, AMI, Award, Compaq, IBM, Packard Bell, Phoenix, Toshiba, and Zenith AMI
BIOS variants. It can also back up, restore, dump, and erase CMOS data.

## OHOS Adaptation Notes

- Upstream is a single-file x86 C program using `outb`/`inb` port I/O and `ioperm`.
- On HarmonyOS PC (aarch64) the recipe gates x86-only code behind
  `__i386__`/`__x86_64__` and provides stubs elsewhere; direct hardware access
  reports that x86 I/O ports are unavailable and points to backup files.
- Supported usage on aarch64 is file analysis: `cmospwd -l backup -m1`
  (load a CMOS backup and run selected decode modules). Hardware read/kill paths
  require x86 and root privileges and are not expected to work on ARM hardware.
- Upstream ships no test suite; automated coverage uses a 128-byte synthetic backup
  plus usage-output checks.

## Dependencies

| Dependency | Version | Note |
|------------|---------|------|
| None | - | Single C file, libc only |

## Function Verification

```bash
cmospwd --help
cmospwd -l cmos_backup.bin -m1
```

## References

- [Official wiki](https://www.cgsecurity.org/wiki/CmosPwd)
- [Source tarball](https://www.cgsecurity.org/cmospwd-5.0.tar.bz2)
