# W0 report: abiword-plugin-gdict 3.0.8

## Dependency graph

```text
abiword-plugin-gdict/3.0.8
|-- boost/1.90.0.3
|-- glib/2.84.0.1.1
|-- libgsf/1.14.58
|-- wv/1.2.9
|-- libxslt/1.1.45.2
|-- libxml2/2.15.3.1
|-- fribidi/1.0.16
|-- libpng/1.6.58
|-- libjpeg/10
`-- zlib/1.3.1.1
build-requires: automake/1.18, libtool/2.5.4
runtime host ABI: AbiWord 3.0.8 (resolved by the AbiWord process, not linked as a Conan package)
```

## Checks

- Local version occupancy passed. Conan dependency checks were unavailable on
  Windows, so the authoritative dependency check ran on the OHOS worker.
- Shadow r20 resolved all direct and transitive requirements, including the
  separately adapted `glib/2.84.0.1.1` and `wv/1.2.9` caches.
- `conan create` built and packaged `gdict.so` successfully.
- The ELF ABI smoke test reported `5 passed, 0 failed`.
- L0/L1/L4/L5 passed; L2 skipped because the package has no `bin/` directory.
- The exported r20 package cache is 11,585,221 bytes with SHA256
  `d04876bb52e7b83efdbf7e98f79ff3f5e3357b8180affc824f6fcdf0721e6d90`.

## Decision

W0 dependencies are ready and the full single-package shadow validation passed
in run `codex-gdict-r20-abiword-plugin-gdict-abiword-plugin-gdict-3.0.8-shadow-r20-20260822-033547-4513`.
The dependency adaptations remain isolated in their own branches. No recipe or
test blocker remains for abiword-plugin-gdict 3.0.8.
