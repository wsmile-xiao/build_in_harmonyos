# ndiff

ndiff compares text files that should be identical or numerically similar and
reports only numeric fields whose absolute or relative error exceeds the chosen
tolerance.

## Usage

```bash
ndiff [options] infile1 infile2
```

Common options include:

| Option | Description |
|--------|-------------|
| `--relative-error n` | Set relative error tolerance |
| `--absolute-error n` | Set absolute error tolerance |
| `--fields spec` | Restrict comparison to selected fields |
| `--quiet` | Suppress ordinary diagnostic output |
| `--version` | Print version and arithmetic precision |

## Build

- Build system: Autotools
- Version: 2.00 upstream. The task platform displayed version `2`, but Conan
  rejects bare integer version `2`, so the package reference uses `ndiff/2.00`.
- License: GPL-2.0-or-later
- Upstream homepage: https://www.math.utah.edu/~beebe/software/ndiff/
- Official distribution: ftp://ftp.math.utah.edu/pub/misc/ndiff-2.00.tar.gz

## OHOS Adaptation

- Uses native clang with the upstream Autotools build.
- Builds the default native long-double precision variant without optional GMP.
- Runs upstream `make check`, which executes 26 comparison cases.
- Overrides `LN=cp` during build/test because HMDFS rejects hard-link creation.
- Overrides `TMPDIR` during `make check` because `/tmp` is read-only on the
  tested OHOS PC environment.
- Packages the built executable manually because upstream `make install` ignores
  Conan `DESTDIR` and tries to write to system paths.
