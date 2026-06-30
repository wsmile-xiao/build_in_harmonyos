# audacious-plugins 4.5.1 测试报告

## 测试日期
2026-05-29

## 测试环境
- OS: HarmonyOS (aarch64)
- Compiler: clang/clang++

## make check
audacious-plugins 无 make check 测试套件。以 staging 验证替代。

## Staging 验证

- 32个插件 .so 文件正确安装到 DESTDIR staging 目录
- Input插件(9): metronom, psf, tonegen, vtx, xsf, flac, vorbis, mpg123, console
- Output插件(4): alsa, oss4, pulse, filewriter
- Effect插件(10): background_music, bitcrusher, compressor, crossfade, crystalizer, echo, mixer, silence-removal, stereo, voice_removal
- General插件(2): mpris2, song_change
- Container插件(6): asx, asx3, audpl, m3u, pls, xspf
- Transport插件(1): gio
- 48个locale .mo 文件正确安装

## 结论
PASS - 所有插件成功编译并安装
