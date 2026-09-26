# libblzf

Conan package for the task-listed `libblzf` name, using upstream [liblzf](https://software.schmorp.de/pkg/liblzf.html) 3.6.

- Portable C LZF compression library and `lzf` command line tool.
- Upstream archive: 56 KB; no external Conan requirements.
- Upstream source contains no test suite; the package runs five C API consumer cases and one CLI round-trip/rejection case on OHOS.
- Static library artifact: `lib/liblzf.a`; header: `include/lzf.h`; executable: `bin/lzf`.
