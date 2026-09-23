# i686-elf-gcc

GNU GCC cross-compiler for the `i686-elf` (bare-metal) target, built to run on
HarmonyOS PC (aarch64). Version 14.2.0 provides the C and C++ frontends plus a
freestanding `libgcc`; the compiler drives the assembler/linker/archiver from
the sibling `i686-elf-binutils` package.

This is the compiler half of the i686-elf cross-toolchain:
`i686-elf-binutils` + `i686-elf-gcc`.

The recipe uses only GNU/GCC official source archives (gcc plus the in-tree
gmp/mpfr/mpc prerequisites selected by `contrib/download_prerequisites`).
HarmonyOS CI validation remains pending until the official worker runs.
