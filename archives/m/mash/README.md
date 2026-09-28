# Mash for HarmonyOS PC

Mash estimates genomic sequence distances using MinHash sketches.
The `2.3` package contains the `mash` command for aarch64 HarmonyOS PC.

Install with Conan from the OHPCD remote:

```sh
conan install --requires=mash/2.3 -r=ohpcd
```

The [version recipe](2.3/conanfile.py) builds against published Cap'n Proto,
GSL and zlib packages. It runs Mash's bundled reference-output tests and a
separate consumer test against the installed executable.
