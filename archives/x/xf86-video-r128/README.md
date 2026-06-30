# xf86-video-r128 — ATI Rage 128 Xorg Video Driver

ATI Rage 128 (R128) video driver for Xorg. Provides basic framebuffer display support
for ATI Rage 128 series GPUs on HarmonyOS/OpenHarmony.

## OHOS Adaptation Notes

- **DRI/EXA disabled**: OHOS xorg-server does not support DRI (Direct Rendering Infrastructure)
  or EXA acceleration. This driver is compiled with `--disable-dri --disable-exa`.
- **Int10 stub**: OHOS xf86int10.h is a stub that does not define `BIOSseg` or `xf86int10Addr`.
  The driver uses `#ifdef __OHOS__` to skip Int10 BIOS reading and falls through to the
  PCI ROM path for VBIOS access.
- **HMDFS fix**: The `umask 077 && mktemp` pattern creates directories that are not writable
  on HarmonyOS's HMDFS filesystem. Patches to config.guess and configure skip umask 077
  on HarmonyOS.

## Dependencies

- xorgproto >= 2024.1
- xorg-server >= 21.1.15
- pixman >= 0.42.2
- libpciaccess >= 0.18

## Install

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- xf86-video-r128 6.13.0
```