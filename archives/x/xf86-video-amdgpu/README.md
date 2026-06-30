# xf86-video-amdgpu

## Description
X.Org video driver for AMD GPU devices using the kernel mode-setting (KMS) interface. This driver supports AMD Radeon GPUs and is the modern successor to the radeon driver.

## Dependencies
- xorg-server >= 21.1.15
- libdrm >= 2.4.89
- libdrm_amdgpu >= 2.4.76
- gbm (stub on OHOS)
- Various X proto packages (xproto, fontsproto, xf86driproto, randrproto, renderproto, videoproto, xextproto)

## OpenHarmony Adaptation
- Glamor (GL-based acceleration) is disabled (--disable-glamor) due to missing real OpenGL/EGL support
- udev support is disabled (--disable-udev) as libudev is not available on OHOS
- GBM (Generic Buffer Manager) uses stub headers/functions since the real library is not available
- Stub headers were created for: gbm.h, GL/gl.h, libgbm_stub.so
- xorg-server.h stub was modified to enable DPMSExtension, DRI3, and DPMSMode constants
- HMDFS umask fix (E011) was applied to configure/config.status

## Install Files
- lib/xorg/modules/drivers/amdgpu_drv.so (Xorg driver module)
- share/man/man4/amdgpu.4 (man page)
- share/X11/xorg.conf.d/10-amdgpu.conf (Xorg config snippet)

## Current Version
- 23.0.0 (built, 2026-06-05)