# GNU Binutils

GNU Binutils is a collection of binary-development utilities including the GNU
assembler, linker, `ar`, `nm`, `objcopy`, `objdump`, `readelf`, `size`,
`strings`, and `strip`.

## HarmonyOS PC adaptation

- Builds native aarch64 command-line tools with the repository OHOS Conan
  profile and upstream Autotools release files.
- Retains the bundled zlib and statically packages internal libraries so the
  tool suite does not publish system-colliding shared libraries.
- Disables `gprofng`, whose collector uses Linux-specific runtime facilities.
- Runs the upstream DejaGNU suites plus an installed-package ELF workflow.

## References

- https://www.gnu.org/software/binutils/
- https://sourceware.org/binutils/
- https://ftp.gnu.org/gnu/binutils/
