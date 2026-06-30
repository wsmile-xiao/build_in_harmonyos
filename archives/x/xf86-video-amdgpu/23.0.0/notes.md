# xf86-video-amdgpu 23.0.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-05
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `ohc-run.py init-build xf86-video-amdgpu 23.0.0 --url=<gitlab-archive-url>`
2. Copied pkg.m4 to m4/ directory (needed for PKG_CHECK_EXISTS macro expansion)
3. `autoreconf -fiv` to regenerate configure
4. Fixed HMDFS umask: `sed -i 's/umask 077/umask 022/g' configure config.status`
5. Created stub gbm.h header and gbm.pc pkg-config file (gbm library not available on OHOS)
6. Created stub GL/gl.h header (glamor disabled, but header still needed for some checks)
7. Enabled DPMSExtension and DRI3 in xorg-server.h stub header (DPMSModeOn and dri3_screen_info_rec needed)
8. Created stub libgbm_stub.so library for linking
9. `./configure --prefix=$DEFAULT_PREFIX --disable-glamor --disable-udev`
10. `make -j1` (succeeded after stub header fixes)
11. `make install DESTDIR=$TEST_PREFIX` (staging install)
12. `make install` (local install to $DEFAULT_PREFIX)
13. Manually created packaging tar.gz with ELF-signed, stripped driver module

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | PKG_CHECK_EXISTS unexpanded in configure | pkg.m4 not in m4/ directory | Copied pkg.m4 from system to m4/ |
| 2 | config.status permission denied (HMDFS) | E011: umask 077 creates dirs owned by different UID | `sed -i 's/umask 077/umask 022/g' configure config.status` |
| 3 | gbm.pc/pkg-config not found | gbm library not available on OHOS | Created stub gbm.h, gbm.pc, libgbm_stub.so |
| 4 | GBM_FORMAT_* uses __uint32_t | glibc internal type, musl doesn define it | Changed to uint32_t in stub gbm.h |
| 5 | GBM_FORMAT_ARGB1555 undefined | Missing from initial stub gbm.h | Added GBM_FORMAT_ARGB1555 and GBM_FORMAT_R8 |
| 6 | DPMSModeOn undeclared | DPMSExtension not enabled in xorg-server.h stub | Enabled DPMSExtension + added DPMSMode constants |
| 7 | dri3_screen_info_rec unknown type | DRI3 not enabled in xorg-server.h stub | Enabled DRI3 define |

## 源码修改

No source code patches needed - all fixes were via stub headers and configure flags.

## Stub headers created/modified

- `/usr/local/include/gbm_stub/gbm.h` - Full stub GBM header with inline functions
- `/usr/local/lib/pkgconfig/gbm.pc` - Stub pkg-config pointing to gbm_stub
- `/usr/local/lib/libgbm_stub.so` - Minimal stub shared library (ELF signed)
- `/usr/local/include/GL/gl.h` - Minimal stub GL header (types + constants)
- `/usr/local/include/xorg/xorg-server.h` - Modified: enabled DPMSExtension, DRI3, added DPMSMode constants

## 依赖版本

- xorg-server >= 21.1.15 (stub headers)
- libdrm >= 2.4.133 (real library)
- libdrm_amdgpu >= 2.4.133 (real library)
- gbm >= 21.1.15 (stub)
- xproto >= 7.0.33
- fontsproto >= 2.1.3
- xf86driproto >= 2.1.1
- randrproto >= 1.6.0
- renderproto >= 0.11.1
- videoproto >= 2.3.3
- xextproto >= 7.3.0

## Configure options

```
--prefix=/storage/Users/currentUser/usr/local
--disable-glamor
--disable-udev
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| amdgpu_drv.so | 141696 (before strip) | Xorg AMDGPU driver module |
| xf86-video-amdgpu-23.0.0-ohos-aarch64.tar.gz | 128038 | Precompiled package (stripped, ELF-signed) |

## 注意事项

- Glamor (GL-based acceleration) is disabled due to missing real GL/EGL support
- udev support is disabled (not available on OHOS)
- GBM functions are stubs returning NULL/0 - driver module won functionally without real GBM
- The driver module can be loaded by xorg-server but won drive actual AMD hardware on OHOS
- Similar stub approach was used successfully for xf86-video-dummy, fbdev, and nv drivers
---

**编译结束**: 2026-06-05 20:42
**最终状态**: built
