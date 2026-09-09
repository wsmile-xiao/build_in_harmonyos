# CI #40901 ELF mode regression

- PR: `OpenHarmonyPCDeveloper/build_in_harmonyos#8573`
- Build: `#40901`
- Failure: import of the final wheel failed with `Permission denied` for
  `pygame/base.cpython-312-aarch64-linux-ohos.so` after the second pip install.
- Earlier target run: G2 and W3 functionality passed; its wheel ZIP entries had
  executable mode `100770`.

## Root cause

`wheel pack` and the worker's pip extraction can disagree about ELF mode bits.
The recipe signed the ELF files and set filesystem mode before repacking, but it
did not verify the ZIP central-directory mode or reapply the mode after pip
extracted the wheel. On the failing worker the loader therefore saw a regular
non-executable file.

## Fix

- `_normalize_wheel_elf_modes()` rewrites only ELF ZIP entries whose mode lacks
  execute bits, preserving file bytes and RECORD hashes.
- `_ensure_elf_executable()` runs after both wheel installations, restores the
  executable bit on materialized ELF files, and fails closed if any ELF remains
  non-executable.
- The mode check runs before the upstream suite, so a future worker variation is
  reported at the packaging boundary rather than as an opaque import failure.

Local synthetic wheel mode regression passes. Existing source patch checks and
the target run 5 functional evidence remain unchanged; a fresh CI/device run
is required for this revision.
