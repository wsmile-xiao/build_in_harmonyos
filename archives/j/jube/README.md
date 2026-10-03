# JUBE (Jülich Benchmarking Environment)

JUBE is a script-based framework for creating benchmark and workflow sets,
running them on different computer systems and evaluating the results. It is
actively developed by the Jülich Supercomputing Centre of Forschungszentrum
Jülich. Benchmark configuration and scripts can be provided in either YAML or
XML format; it supports parameter combinations, platform configs, analyses and
result databases.

## Package contents

- Public Python packages: `jube`, `jube.result_types`, `jube.util`
- Command-line tools: `jube` and `jube-autorun` (bundled under `bin/`)
- Shared data: examples / `platform` (LSF, Moab, PBS, SLURM) / `contrib/schema`
  (dtd/json/rnc/xsd) / `docs/JUBE.pdf`, copied under `share/jube`
- License: GPL-3.0
- Runtime dependency: `pyyaml` (needed for YAML-based benchmark inputs; XML
  inputs work without it)

## OpenHarmony adaptation

- Pure Python noarch package (no C extension). Built with the alabaster /
  python3-distro pattern: `pip install --prefix staging` then relocation of
  `site-packages` / `bin` / `share` into the package.
- Source taken from the official GitHub `REL-2.7.1` git tag archive, because
  the released `JUBE-2.7.1.tar.gz` sdist omits the `tests/` directory; the git
  tag archive contains the upstream unittest suite, which the recipe runs for
  real on OHOS (`run_all_tests.py`, 102 cases).
- `grp` / `pwd` / `sqlite3` are POSIX stdlib modules (present on OHOS, a
  POSIX-like kernel), so the tool runs natively.

## Usage

```bash
# After conan install jube/2.7.1 (buildenv/runenv set PYTHONPATH + PATH)
jube --version
jube run examples/hello_world/hello_world.xml
```
