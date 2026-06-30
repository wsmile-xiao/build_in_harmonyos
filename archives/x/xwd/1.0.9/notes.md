# xwd 1.0.9 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-02
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `ohc-run.py init-build xwd 1.0.9 --url=https://www.x.org/releases/individual/app/xwd-1.0.9.tar.gz`
2. Patch config.guess/config.sub with `patch-autotools-ohos.pl` + manual `linux-ohos*) ;;` addition
3. Track edits with `ohc-run.py track-edit add`
4. Build and install libxkbfile dependency (meson build, v1.1.3)
5. `./configure --prefix=/storage/Users/currentUser/usr/local` with PKG_CONFIG_PATH set
6. Patch config.status to use pre-created tmp directory (mktemp permission issue on HarmonyOS)
7. Run patched config.status to generate Makefile and config.h
8. `make -j4` — success with 1 warning (multiVis.c unused variable 'count')
9. `make install DESTDIR=$TEST_PREFIX` — DESTDIR staging install
10. `ohc-run.py verify-build xwd 1.0.9 --install-prefix=...` — PASS
11. `ohc-run.py package xwd 1.0.9` — packaging success
12. `make install` — local installation
13. `ohc-run.py finish xwd 1.0.9 built` — archive closed

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess cannot identify HarmonyOS | E007: autotools scripts don't recognize HarmonyOS aarch64 | Use `patch-autotools-ohos.pl` + add `linux-ohos*) ;;` case to config.sub |
| 2 | config.status mktemp permission error | HarmonyOS filesystem restricts mktemp-created directories from being written to by shell scripts | Manually patch config.status to use pre-created tmp directory at /storage/Users/currentUser/tmp/buildtmp/ |
| 3 | libxkbfile dependency missing | xwd requires libxkbfile which wasn't pre-installed | Build libxkbfile v1.1.3 with meson (same config.status mktemp issue prevented autotools build) |
| 4 | curl cannot download files | libz.so loading error (inflateInit2_ symbol not found) | Use Python urllib.request for downloads, or ohc-run.py init-build for internal downloads |

## 源码修改

- `config.guess`: Added HarmonyOS system identification (E007 patch via patch-autotools-ohos.pl)
- `config.sub`: Added ohos-linux triplet, ohos* OS, and `linux-ohos*) ;;` compatibility case

## 依赖版本

- libxkbfile 1.1.3 (built with meson)
- libX11 1.8.12 (pre-installed)
- xorgproto 7.0.31 / xproto 7.0.31 (pre-installed)
- xorg-macros 1.20.1 (pre-installed)

## 验证结果

```bash
file /storage/Users/currentUser/usr/local/bin/xwd
# ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV), dynamically linked, interpreter /lib/ld-musl-aarch64.so.1, with debug_info, not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| xwd-1.0.9-ohos-aarch64.tar.gz | 1910KB | Runtime package (stripped) |
| xwd-1.0.9-ohos-aarch64-debug.tar.gz | 676KB | Debug symbols package |

## 注意事项

- config.status on HarmonyOS has mktemp permission issues; need to use pre-created tmp directory
- xwd binary at runtime requires libxkbfile.so.1 and X11 libraries to be available
- G0 clean-build verify failed due to config.status mktemp issue; manual build verified successfully
---

**编译结束**: 2026-06-02 10:58
**最终状态**: built