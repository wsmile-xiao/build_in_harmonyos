# words-es 2.1

> GNU Aspell Spanish word list packaged as a portable UTF-8 text resource.

## Overview

This Conan package converts the official GNU Aspell Spanish 1.11-2 `es.cwl`
word list into a sorted, unique UTF-8 file. It contains 56,329 entries and
does not require Aspell at build or runtime.

## HarmonyOS use

The package installs the list at `share/dict/words-es` and exports its absolute
path through `WORDS_ES_FILE` for both the build and runtime environments. The
resource is architecture-independent, so the same package contents apply to
HarmonyOS PC x86_64 and AArch64.

## Verification

`conan create` builds and runs a C++ consumer that checks the packaged path,
entry count, UTF-8 Spanish words, strict ordering, uniqueness, and removal of
Aspell affix metadata. The accompanying HarmonyOS test additionally checks
the native OS and machine identity on an x86_64 emulator.

## License and source

The upstream Spanish dictionary is licensed under GPLv2. The package includes
the upstream `Copyright` notice under `licenses/`.

- [GNU Aspell Spanish dictionary source](https://ftp.gnu.org/gnu/aspell/dict/es/)
- [GNU Aspell dictionary index](https://ftp.gnu.org/gnu/aspell/dict/0index.html)
