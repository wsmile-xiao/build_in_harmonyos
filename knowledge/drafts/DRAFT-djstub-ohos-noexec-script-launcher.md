# DRAFT - Native ELF launchers for packaged scripts on OHOS

> Status: DRAFT | Source: djstub 0.7 PR #5156, commit `4b782acc6d36`

## Failure signature

An application package installs a shell or Bash script under `bin/`. The file
has execute bits and names an existing interpreter, but direct invocation on a
HarmonyOS PC still fails before the script body runs:

```text
Permission denied
exit status 126
```

Changing the shebang or repeating `chmod +x` does not fix the command.

## Root cause

The script resides in a user-data or package staging location that does not
permit direct execution of script objects. Script execution requires the kernel
to accept the script first and then dispatch its shebang interpreter. A noexec
policy blocks that first step even when `/data/service/hnp/bin/bash` exists.

This is narrower than a missing-interpreter problem. It also differs from a
launcher that selects among executable interpreters: the trusted interpreter is
known, while the package must expose several upstream scripts as normal PATH
commands.

## Packaging pattern

1. Install upstream scripts as non-entry-point package data under
   `libexec/<package>/`.
2. Build one small target-native ELF launcher and copy it to each public command
   name under `bin/`.
3. Resolve the script relative to `/proc/self/exe`; do not bake a Conan cache or
   staging path into the binary.
4. Allow-list `argv[0]` before selecting a script.
5. Invoke the fixed HNP Bash with `execv()` and an argv array. Do not use
   `system()`, `popen()`, or `bash -c`.
6. Add the HNP tool directory to `PATH` when upstream scripts call platform
   tools such as `llvm-strip`.

The djstub package applies this pattern to `djlink`, `djstrip`, and
`djelfextract`, while keeping the upstream scripts in `libexec/djstub/`.

## Verification

The consumer test must exercise each installed public command, not only inspect
the package layout:

```sh
test "$(djlink -v)" = "djstubify version 0.7"
test "$(djstrip)" = "Usage: djstrip <file_name>"
test "$(djelfextract)" = "Usage: djelfextract <solib_name> <out_elf>"
```

Also verify that the public `bin/` entries are ELF executables and that scripts
remain package-relative after relocation.
