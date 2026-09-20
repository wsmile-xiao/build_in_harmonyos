# libopusenc

Conan packaging for the high-level Ogg Opus encoding library.

## HarmonyOS PC adaptation

- Versions: `0.2.1`, `0.3`
- Build system: Autotools
- Dependencies: `opus/1.5.2.1` (the bundled `ogg_packer` needs no libogg)
- Outputs: `libopusenc`, in shared or static form

The bundled platform scripts are patched to recognize the
`aarch64-unknown-linux-ohos` tuple (0.3 needs no `config.sub` patch: its
newer `config.sub` accepts `linux-ohos` natively). Shared OHOS builds use a
real unversioned `libopusenc.so` file.

The upstream release registers no test entry (`Makefile.am` has no `TESTS`
or `check_PROGRAMS`). Its example encoder is a `noinst` demo, not a
registered test. The Conan consumer is one independent integration entry
and is counted once across shared and static builds.
