# python3-distro (distro)

`distro` is a widely used pure-Python library (a dependency of pip/pipx)
that reads OS distribution information from `/etc/os-release`, `*-release`
files and the `lsb_release` command, exposing `id()/name()/version()/
like()/codename()` and a full `info()` dict.

## Package contents

- Public Python package: `distro` (import name)
- Command-line tool: `distro` (console_script `distro.distro:main`),
  `python -m distro` also works
- License: Apache-2.0
- Runtime dependencies: none

## OpenHarmony adaptation

- Packages the architecture-independent Python sources directly
  (noarch, alabaster precedent: `pip install --prefix staging` +
  site-packages relocation). No compiler involved.
- Upstream 158-case pytest suite measured on-device (OHOS):
  `1 passed, 233 skipped` — the skips come from the upstream
  `IS_LINUX = sys.platform.startswith("linux")` guard, since OHOS
  reports `sys.platform == "ohos"`. Core parsing logic is platform
  independent; `test_package` carries upstream `resources/distros`
  subsets (arch/ubuntu14/centos7/centos5) and re-asserts the same
  expectations: 12/12 pass.
- Host detection on an OHOS machine returns empty values because
  HarmonyOS does not ship `/etc/os-release`; this is the library's
  documented unknown-distro branch, not a defect. If OpenHarmony ever
  provides `/etc/os-release`, distro will pick it up without changes.

## Usage

```bash
# After conan install python3-distro/1.9.0
export PYTHONPATH=$CONAN_PREFIX/lib/python3.12/site-packages:$PYTHONPATH
python3 -c "import distro; print(distro.info())"
python3 -m distro   # CLI: Name/Version/Codename
```
