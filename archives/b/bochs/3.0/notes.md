# Bochs 3.0 HarmonyOS PC adaptation

## Scope

This entry packages upstream tag `REL_3_0_FINAL` as `bochs/3.0`. The package
contains the headless x86/x86-64 emulator, `bximage`, BIOS/VGA firmware,
keymaps, manuals and license documents.

## Path C difficulty rationale

Bochs is a system emulator with a large C/C++ dependency graph, generated CPU
decoder sources, architecture-specific CPU/FPU/VMX models, virtual devices and
guest firmware. A full validation boots x86 firmware inside an AArch64
HarmonyOS process, so compilation alone is insufficient. This satisfies the
Path C criteria for complex architecture and high full-test cost. In
particular, the adaptation crosses two architecture boundaries at once: an
AArch64 OHOS host binary implements an x86/x86-64 CPU and then executes packaged
x86 BIOS/VGA firmware. Bochs 3.0 also has no portable `make check` target, so a
meaningful regression check must combine command-unit coverage with a bounded
guest-firmware execution test. Its optional SDL/X11, terminal, readline and
plugin dependency graph further requires an explicit, tested feature boundary.

## Dependency boundary

The available HarmonyOS artifact repository does not publish SDL, ncurses or
readline packages usable by this task. The recipe therefore builds a functional
headless core with `nogui`, disables SDL/terminal frontends, readline and
loadable plugins, and keeps the internal debugger enabled. This is an explicit
feature boundary, not a stub: the test starts the emulator, executes guest BIOS
code and verifies the expected no-boot-device panic.

## Portability changes

1. `config.guess` maps native HarmonyOS machines to `*-unknown-linux-ohos`.
2. `config.sub` accepts the `linux-ohos` operating-system suffix used by Conan.
3. `gui/keymap.cc` includes `<libgen.h>` on OHOS for POSIX `basename`.
4. The recipe creates three generated VPATH directories omitted by the Bochs
   3.0 makefiles before compiling.
5. A narrow patch relaxes only the two `confXXXXXX` temporary-directory masks
   from `umask 077` to `022` for HMDFS build workers. The recipe no longer
   performs a global generated-`configure` rewrite.
6. Windows build hosts run the POSIX `configure` and Make commands through the
   MSYS2 shell selected by the Conan profile. The recipe invokes `configure`
   through a relative source path so Autoconf does not split a `C:/...` path at
   the drive separator, and excludes only install-directory arguments from
   MSYS conversion. Native HarmonyOS builds are unaffected.

## Knowledge scope

The Windows/MSYS2 build decisions are retained in this archive note for
traceability. This PR does not modify files outside `archives/`, so it does not
claim a separate Path B knowledge contribution.

## Verification

A formal Conan 2 cross-build from Windows/MSYS2 with the DevEco OHOS Clang
15.0.4 profile completed for `os=OHOS`, `arch=armv8`. All four portability
patches applied, configure detected `aarch64-unknown-linux-ohos`, compilation
and `make install` completed, and Conan created package revision
`0d8c480b68c87f4cded6c5d59c45eb96`. The package contains 48 payload files:
two commands, 17 root firmware/share files, 16 keymaps, nine documents and four
manual pages. Both commands are ELF64 AArch64 PIE executables with no RUNPATH;
their only `DT_NEEDED` entries are `libc++_shared.so` and `libc.so`.

The exact formal package was transferred with archive and per-binary SHA256
verification, signed in place on a HarmonyOS PC 1.12.0 AArch64 target, and
tested using the repository scripts without changing their assertions. All
three `bximage` command-unit cases passed (10/10 assertions): option parsing and
invalid-mode rejection, deterministic 10 MiB flat-image creation, and
image-mode/geometry reporting. The headless guest-BIOS functional case also
passed (6/6 assertions): both commands executed, Bochs loaded the packaged
BIOS/VGA firmware, and `bochs.log` contained `No bootable device.`. The result
is 4/4 tests (100%) and 16/16 assertions (100%).

Conan's cross-build `test_package` correctly reports `can_run=false` on the
Windows build host and does not claim target execution there. The separate
native-device run supplies the target evidence while preserving that boundary.
