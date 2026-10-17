# liblcf-tools

`liblcf-tools` packages the command-line utilities shipped by the EasyRPG
Project's `liblcf` source tree:

- `lcf2xml` converts RPG Maker 2000/2003 LCF files (LDB/LMT/LMU/LSD) to XML
  and back.
- `lcfstrings` extracts text and filename strings from LCF files.

## Upstream

- Project: <https://github.com/EasyRPG/liblcf>
- Version: 0.8.1
- Source: <https://github.com/EasyRPG/liblcf/archive/refs/tags/0.8.1.tar.gz>
- SHA-256: `5ec89082d54f1a29d23fed54de70acab4375036d57828ff0fc7a88b81833d40f`
- License: MIT

This is an application package distinct from the `liblcf` development-library
archive. The package builds the upstream library internally as a static target,
then installs only the two tools and the license.

## Usage

```text
lcf2xml input.xml       # writes the corresponding LCF file
lcf2xml input.lmt       # writes XML
lcfstrings game.lmt
```

The HarmonyOS PC recipe enables XML support through the published
`expat/2.8.2.1` Conan dependency, keeps the upstream INI unit tests enabled
through `inih/r58`, and enables the upstream ICU Unicode conversion path with
`icu4c/77`.
