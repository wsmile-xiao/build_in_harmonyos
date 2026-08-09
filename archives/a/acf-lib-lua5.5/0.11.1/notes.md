# acf-lib-lua5.5 0.11.1 adaptation notes

The recipe packages all eight Lua modules from the immutable upstream
`v0.11.1` tag. It installs them under `share/lua/5.5/acf` and duplicates the
upstream compatibility-link names at `share/lua/5.5` so packaging does not
depend on host symlink privileges.

Lua 5.5 makes generic-for control variables read-only. Three functions in
upstream `format.lua` reuse the loop value as a mutable working variable, so
the module otherwise fails while loading. The portability patch copies each
control value to a local mutable variable without changing the parsing logic.

The package requires `lua/5.5.0`. The independently usable `format`, `html`,
and `validator` modules depend only on the Lua standard library. The `fs`,
`date`, and `processinfo` modules additionally require a POSIX module; `apk`,
`db`, and `processinfo` additionally use `subprocess`; database operations need
the selected LuaSQL driver. Those system-facing capabilities are not replaced
with test stubs or reported as validated here.

Alpine aports declares `options="!check" # no test suite`, and the v0.11.1
source has no test directory or test/check target. Upstream testing is therefore
not applicable with zero upstream tests, rather than a `0/0 passed` claim.

The added C consumer embeds the packaged Lua 5.5 library, sets `package.path`
to the real Conan package, loads `acf.format`, `acf.html`, `acf.validator`, and
the top-level compatibility module, invokes their APIs, and confirms malformed
IPv4 input and an out-of-range port are rejected.

## Validation performed on 2026-08-09

- Linux Conan Release: package inventory 16 Lua files; positive consumer and
  invalid-input scenarios passed.
- Linux Conan Debug: package inventory 16 Lua files; positive consumer and
  invalid-input scenarios passed.
- OHOS aarch64 Release: Conan create and test-package cross-build passed; the
  consumer and linked Lua archive contain ELF64 AArch64 objects.
- OHOS x86_64 Release: Conan create and test-package cross-build passed; the
  consumer is ELF64 x86-64.
- HarmonyOS PC emulator (`x86_64`): all 16 packaged Lua files were pushed from
  the Conan package; both the positive consumer and invalid-input scenario
  passed on target.
