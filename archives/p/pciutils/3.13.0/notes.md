# pciutils 3.13.0 — Build Notes

> Archive created: 2026-04-25
> Last updated: 2026-08-07

## Basic Info
| Item | Value |
|------|-------|
| Software | pciutils |
| Version | 3.13.0 |
| Status | built |
| Build System | makefile |
| Source URL | https://mj.ucw.cz/download/linux/pci/pciutils-3.13.0.tar.gz |

## Build Process

### Problem 1: HarmonyOS Platform Detection
- **Issue**: lib/configure script shows "your OS is not supported by the PCI Library"
- **Cause**: HarmonyOS not in pciutils supported OS list
- **Fix**: Added HarmonyOS → linux mapping in lib/configure (patch 0002)

### Problem 2: Compiler Not Found
- **Issue**: Makefile defaults to CC=cc which doesn't exist on HarmonyOS
- **Cause**: Only clang is available, no cc symlink
- **Fix**: Changed CC=cc to CC=clang in Makefile (patch 0001)

### Problem 3: HMDFS Symlink Issues
- **Issue**: ln -sf fails on HMDFS filesystem
- **Cause**: HarmonyOS filesystem doesn't support symlinks properly
- **Fix**: Replaced ln -sf with cp -a in Makefile install targets (patch 0001)

## Patches Applied
| File | Description | Type |
|------|-------------|------|
| 0001-Makefile.patch | Fix compiler to clang, replace ln -sf with cp -a | portability |
| 0002-lib-configure.patch | Add HarmonyOS to linux platform mapping | portability |

## Build Result
- ✅ Compilation successful
- ✅ conan create successful (G2 PASS)
- ✅ Local CI simulation (W3) PASS
- ✅ All conan-verify gates pass (G1-G4, L2/L4/L5)

## Known Limitations
- PCI hardware access requires root/ELF signature on device
- Functional testing on-device requires signing

## 结束

**编译结束**: 2026-08-07
**最终状态**: built — Conan adaptation complete, all verification gates pass
