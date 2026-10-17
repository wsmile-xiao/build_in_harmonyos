# afmize

afmize generates atomic-force microscopy images from PDB structures. Version 2.0.2 is packaged as a Conan application and installs `bin/afmize`; the upstream `simulator` target is intentionally not installed.

## Usage

```sh
afmize config.toml
```

The package recipe vendors the exact upstream mave, pnm, and toml11 snapshots from fixed archives. Build configuration is offline after Conan sources and dependencies are available.
