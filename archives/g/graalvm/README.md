# GraalVM for OpenHarmony PC

This software archive contains two version-specific package contracts. Version
23.1.6 provides the UPL-1.0 GraalVM SDK JAR for embedding and Polyglot APIs.
Version 25.0.3 provides a headless OpenHarmony PC adaptation of the official
GraalVM Community JDK Linux aarch64 distribution, including Native Image.

## Version 25.0.3 Features

- Java 25 runtime and development tools
- Graal compiler and Native Image
- Relocatable, self-signed AArch64 ELF executables and libraries
- Headless AWT and font support through the packaged Conan dependency

## OpenHarmony Adaptation

The upstream distribution targets GNU libc. The recipe rewrites the fixed
GNU loader and SONAME references to equal-or-shorter OpenHarmony-compatible
names, builds private `libg.so` and `libjz.so` compatibility libraries, and
self-signs every packaged ELF. Each Native Image entry is a signed AArch64 PIE
launcher with a same-directory isolated Python companion. The companion uses
the OpenHarmony Clang toolchain, limits compilation to one processor and 1 GiB
of Java heap, and finalizes each generated executable with a relocatable RPATH
and its matching private compatibility library. OpenHarmony builds must provide
`-o` or `--output` so failed or interrupted finalization can restore that exact
path without touching unrelated working-directory files.

The package intentionally has a headless support boundary. It retains
`libawt_headless.so` and `libfontmanager.so`, while removing `jconsole`, X11
AWT/JAWT, sound, and splash-screen ELFs whose published runtime and display
closure is not available on the validated OpenHarmony target. The exact scope
evidence and submission gate are recorded in
`25.0.3/notes.md`.

## Dependencies

- `freetype/2.14.3` for headless font-manager loading
- OpenHarmony Clang, LLVM ELF tools, `patchelf`, and `binary-sign-tool` as
  platform build tools
- gcompat 1.1.0 and zlib 1.3.2 are built privately by this recipe

Version 23.1.6 is a prebuilt Java SDK JAR and does not provide a Java runtime,
the `native-image` command, or the 25.0.3 platform adaptation described above.

## References

- https://www.graalvm.org/
- https://github.com/graalvm/graalvm-ce-builds
- https://git.adelielinux.org/adelie/gcompat
- https://github.com/madler/zlib
