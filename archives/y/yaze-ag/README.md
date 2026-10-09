# yaze-ag/2.51.3 for HarmonyOS PC

YAZE-AG is a Z80/CP/M emulator. This recipe builds native AArch64 `yaze_bin` and `cdm` with the upstream ARMv8 Makefile, plus a relocatable `yaze` launcher. The package includes upstream boot files, key maps, and two disk images used by the consumer test. It does not install into system directories or run upstream's destructive `make install` target.

On the tested HarmonyOS PC, the upstream `monitor.c` cannot compile because it relies on glibc-private `__S_IFMT`, `__S_IFREG`, and `__S_IFDIR` names. The patch replaces file-type comparisons with portable POSIX `S_ISREG` and `S_ISDIR`. The consumer test boots the installed emulator, mounts both packaged disks, lists the mounts, and exits normally.

This is not a full Z80 instruction-regression or CP/M application-suite result. The upstream release archive does not contain the `test/` sources referenced by its Makefile, so those tests were not run. Other bundled disk images and the interactive first-run setup script are not packaged.
