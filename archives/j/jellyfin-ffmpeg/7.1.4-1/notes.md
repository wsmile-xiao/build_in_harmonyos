# Adaptation Notes — jellyfin-ffmpeg 7.1.4-1
Build Date: 2026-08-06
Source: https://github.com/jellyfin/jellyfin-ffmpeg/archive/refs/tags/v7.1.4-1.tar.gz
SHA256: 154a857fecf14edb1f91bb8919ea7e7e4f6a7fd592023319b4db4ad39a2bee74
Build System: FFmpeg custom configure + make
Key Adaptations:
1. --target-os=linux (uname -s returns HarmonyOS)
2. Clear env pollution, set PKG_CONFIG_PATH to conan .pc
3. Fix fribidi.pc Cflags (-I${includedir}/fribidi)
4. --enable-gpl + --enable-version3 + --enable-nonfree (fdk-aac/gmp)
5. --disable-stripping + binary-sign-tool (ELF signatures)
6. Relocate .pc libdir/includedir
Missing deps (not in conan registry): x264, x265, svt-av1, chromaprint, libdrm, libass, libbluray, theora, openmpt, zvbi, opencl (no ICD loader)
Soname: avcodec 61 / avformat 61 / avutil 59 / avdevice 61 / avfilter 10 / swscale 8 / swresample 5

## 关闭
COMPLETED: jellyfin-ffmpeg 7.1.4-1 built and verified
