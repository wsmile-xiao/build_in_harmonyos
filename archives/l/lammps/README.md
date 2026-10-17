# lammps

Large-scale Atomic/Molecular Massively Parallel Simulator (LAMMPS) molecular
dynamics code, packaged as an OHOS-native command line tool.

- Upstream: https://www.lammps.org / https://github.com/lammps/lammps
- License: GPL-2.0-only
- Build system: CMake (project root is the `cmake/` subdirectory of the release)

## Versions

| Version | Upstream tag | Status | Artifact |
|---|---|---|---|
| 20260211 | `patch_11Feb2026` | built | `bin/lmp` |

## Usage

```sh
lmp -in in.lj -log log.lammps
lmp -h          # note: this build rejects -version / --version / --help (upstream src/lammps.cpp:490)
```

The upstream benchmark inputs ship with the sources under `bench/`
(`bench/in.lj`, `bench/in.eam`, ...); `bench/in.lj` is the input used by this
archive test package.

## Adaptation notes

See [20260211/notes.md](20260211/notes.md). Highlights: the CMake project root
of this release is `cmake/CMakeLists.txt` (there is no `CMakeLists.txt` at the
source root), so the recipe configures with `build_script_folder="cmake"`;
the build is hermetic (no downloads, no external libraries) and therefore uses
the plain stock package set with every `PKG_*` that needs an external library
or a network download switched off explicitly.
