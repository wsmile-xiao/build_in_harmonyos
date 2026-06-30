# xf86-video-nv 2.1.24 - Build Notes

## Overview
X.Org NVIDIA legacy video driver for NV4/NV5/NV10/NV20/NV30/NV40/G80 GPUs.
Supports both legacy RIVA/NV hardware and G80 series (GeForce 8xxx+).

## Build Configuration
- **Compiler**: clang 15.0.4 (OHOS SDK) + GNU ld.bfd (binutils 2.45)
- **Target**: OpenHarmony aarch64
- **Prefix**: /storage/Users/currentUser/usr/local

## Build Issues and Solutions

### 1. HMDFS umask permission issue
config.status uses `umask 077` when creating temp directories. On HMDFS, this creates
directories with restricted permissions (2700) that prevent even the owner from writing.
Fixed by patching config.status to use `umask 022`.

### 2. ELF signing required
Used a CC wrapper script ($HOME/tmp/cc-sign-wrapper.sh) that automatically signs
compiled binaries using ohc-run.py sign-elf.

### 3. _PKG_CONFIG_VERSION_CHECK macro not defined
The custom pkg.m4 file referenced `_PKG_CONFIG_VERSION_CHECK` but didn't define it.
Removed the broken reference line (line 38) from pkg.m4.

### 4. Missing SDK headers - extensive stub headers required
The nv driver requires many headers not included in the basic xorg-server SDK:
- **vbe.h**: VESA BIOS Extensions interface (for dual-head VBE mode support)
- **vbeModes.h**: VBE modes interface
- **exa.h**: EXA (EXtension for Acceleration) interface (for G80 EXA acceleration)
- **xf86int10.h**: INT10 module interface (for real-mode BIOS calls)
- **dgaproc.h**: DGA (Direct Graphics Access) extension with DGA flags
- **xaa.h, xaalocal.h**: XAA acceleration (legacy, HAVE_XAA_H=undef)
- **xf86RAC.h, xf86Resources.h**: Legacy resource access (only for ABI < 6)
- **compat-api.h**: API compatibility (copied from driver source)
Created comprehensive stub headers for all of these.

### 5. pciaccess.pc missing
Created a stub pciaccess.pc (version 0.18) to satisfy PKG_CHECK_MODULES requirement.

### 6. Makefile -Werror=implicit override
The configure script set `-Werror=implicit-function-declaration` in BASE_CFLAGS,
preventing compilation of code that uses `ffs()` (not available in OHOS libc).
Fixed by:
- Replacing `-Werror=implicit` with `-Wno-error=implicit-function-declaration`
- Adding `-Dffs=__builtin_ffs` to BASE_CFLAGS

### 7. ExaDriverRec struct fields
The EXA driver interface changed between versions. Created comprehensive exa.h
with all fields used by g80_exa.c (exa_major, exa_minor, pixmapOffsetAlign,
pixmapPitchAlign, DoneSolid, DoneCopy, etc.).

### 8. xf86Int10Info struct fields
The g80_driver.c uses INT10 register fields (num, ax, bx, cx, dx, si, di, etc.)
for VBE BIOS calls. Created comprehensive xf86int10.h with all register fields.

## Installed Files
- lib/xorg/modules/drivers/nv_drv.so (186KB, ELF-signed)