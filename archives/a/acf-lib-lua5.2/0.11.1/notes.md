# acf-lib-lua5.2 0.11.1 adaptation notes

The recipe packages all eight Lua modules from the immutable upstream
`v0.11.1` tag. It installs them under `share/lua/5.2/acf` and duplicates the
upstream compatibility-link names at `share/lua/5.2` so packaging does not
depend on host symlink privileges.

## Lua 5.2 needs no patch (unlike the Lua 5.5 port)

`acf-lib-lua5.5` required `patches/0001-lua55-mutable-loop-values.patch` because
Lua 5.5 makes generic-for control variables read-only: `format.lua`'s
`update_ini_file`, `parse_ini_file` and `set_ini_section` reuse the loop value
`l` as a mutable working variable. **Lua 5.2 keeps generic-for loop variables
mutable**, so the same upstream files load and run unmodified.

Proven on the native `aarch64` OHOS build host with the Lua 5.2.4 interpreter
built from the `lua/5.2.4` recipe:

```
$ for f in *.lua; do luac -p "$f"; done   # 8/8 syntax OK
$ lua positive.lua    # loads acf.format/acf.html/acf.validator + top-level
                      # compat 'format', runs update_ini_file/parse_ini_file/
                      # set_ini_section + validation APIs -> POSITIVE PASS
$ lua invalid.lua     # malformed IPv4 + out-of-range port rejected -> INVALID PASS
```

The C consumer embedded in `test_package` repeats these checks against the
real Conan package on every `conan create`.

## Module dependencies

The independently usable `format`, `html`, and `validator` modules depend only
on the Lua standard library. The `fs`, `date`, and `processinfo` modules
additionally require a POSIX module; `apk`, `db`, and `processinfo` additionally
use `subprocess`; database operations need the selected LuaSQL driver. Those
system-facing capabilities are not replaced with test stubs or reported as
validated here.

## Upstream tests

Alpine aports declares `options="!check" # no test suite`, and the v0.11.1
source has no test directory, no test/check target, and a one-line README.
Upstream testing is therefore not applicable with zero upstream tests, rather
than a `0/0 passed` claim. Verification commands and output are recorded in
`reports/upstream-test-verification.md`.

## Validation performed on 2026-08-11 (aarch64 OHOS, clang 15)

- Conan create + test_package cross-build passed with the `ohos-aarch64`
  profile; the consumer and linked Lua archive contain ELF64 AArch64 objects.
- Positive consumer and invalid-input scenarios executed natively on the
  HarmonyOS PC host (host arch == target arch == aarch64).
---

**编译结束**: 2026-08-11 15:22
**最终状态**: built
