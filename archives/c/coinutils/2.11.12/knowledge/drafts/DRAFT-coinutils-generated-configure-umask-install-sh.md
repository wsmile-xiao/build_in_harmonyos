# DRAFT-coinutils-generated-configure-umask-install-sh

> Contributor: coinutils 2.11.12 adaptation | Status: Draft | Updated: 2026-09-08
> Source: archives/c/coinutils/2.11.12

## Symptom

CoinUtils 2.11.12 is an autotools release archive. The generated root and nested
`configure` scripts contain secure temporary-directory patterns with `umask 077`.
The nested generated `CoinUtils/src/Makefile.in` also invokes `install_sh_DATA`
directly when installing `config_coinutils.h`.

On the HarmonyOS target workflow, these generated-file assumptions can be too
fragile for package build directories and staged source trees.

## Root Cause

This package should not regenerate autotools files on the target. The release
archive already includes generated scripts, and adding `automake`/`autoconf`
tool requirements would create a separate toolchain adaptation problem. The
stable fix is therefore a small OHOS-scoped generated-file adjustment inside
the Conan recipe:

- change configure temp-directory creation from `umask 077` to `umask 002`
- call `install_sh_DATA` through `$(SHELL)` for `config_coinutils.h`
- apply the configure replacement to both root and nested configure scripts

## Recommended Handling

Keep the mutation narrow and target-scoped:

```python
if str(self.settings.os) == "OHOS":
    for relative_path in ("configure", os.path.join("CoinUtils", "configure")):
        replace_in_file(self, configure, "(umask 077 && mkdir $tmp)", "(umask 002 && mkdir $tmp)")
        replace_in_file(self, configure, "umask 077 && mktemp -d", "umask 002 && mktemp -d")
```

For the install helper:

```python
replace_in_file(
    self,
    os.path.join(self.source_folder, "CoinUtils", "src", "Makefile.in"),
    "\t$(install_sh_DATA) config_coinutils.h",
    "\t$(SHELL) $(install_sh_DATA) config_coinutils.h",
)
```

## Evidence

The OHOS branch of `conanfile.py` performs these replacements before configure.
The package then configured, built, installed, and passed the signed
`test_package` smoke on the target worker.

## Reuse Boundary

This draft applies to generated autotools release archives. It should not be
used as a blanket instruction to run `autoreconf` or add autotools
`tool_requires` to every package. If upstream source lacks generated configure
files, adapt autotools as a separate dependency path instead.
