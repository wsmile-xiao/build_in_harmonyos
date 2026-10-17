# keyboards-rg 0.3-nmu2 HarmonyOS adaptation notes

## Source and version

- Canonical Debian source version: `0.3+nmu2`.
- Conan/archive version: `0.3-nmu2`, matching the requested archive path.
- Source URL: `https://deb.debian.org/debian/pool/main/k/keyboards-rg/keyboards-rg_0.3%2Bnmu2.tar.xz`.
- Source SHA256: `D3139512D68C2A93DB71315F3D1ECEB431DA237C47F4A723F87F9BB62D8D3DF4`.
- The source is a Debian-native `Architecture: all` data package. Its `debian/rules` contains no project build system beyond debhelper delegation.

## Upstream payload and tests

The Debian install manifest contains:

- `layouts-xkb/eo_rg`, `pancyr`, `sk_rg`, and `sk_snk`;
- `layouts-console/ru_rg.kmap` and `sk_rg.kmap`;
- `scripts/cyrx`, `scripts/eox`, and `scripts/skx`;
- `COPYING`.

The source has no runnable upstream test command. `test/slgul_rg` is an XKB layout fixture, not a registered test executable, and `debian/rules` has no test target. This is recorded in `test_package/MANIFEST.yml` as zero upstream tests.

## HarmonyOS adaptation

No source patch is required. The recipe accepts Linux and OHOS settings, clears the target-dependent Conan package ID, and packages the Debian payload into relocatable Conan paths instead of `/usr`:

- XKB symbols: `share/X11/xkb/symbols/`;
- console maps: `share/keymaps/i386/qwerty/`;
- helper scripts: `bin/`;
- license: `licenses/COPYING`.

The recipe exposes `KEYBOARDS_RG_XKB_DATA_DIR` and `KEYBOARDS_RG_CONSOLE_MAP_DIR` through Conan build/run environments. Debian's `xkb-data` and `xserver-xorg` relationships remain platform runtime expectations and are not modeled as Conan link requirements.

## Consumer validation

`test_package/test_keyboards_rg.py` is source-bound to the official archive hash and every installed-file hash. It checks file closure, non-empty payloads, XKB declarations, console keymap headers, license presence, absence of `oldfiles`, and absence of hard-coded system paths. `test_keyboards_rg.sh` performs the same checks with HarmonyOS base utilities so it does not depend on Python being installed.

On OHOS it executes all three packaged helper scripts through the target `/bin/sh`: `eox`, `skx`, and `cyrx` with its default, Ukrainian, and Belarusian variants. A temporary target-side `setxkbmap` recorder is placed first in `PATH`, and the test verifies the five exact backend invocations before emitting `KEYBOARDS_RG_OHOS_FLOW=PASS invocations=5`. This exercises the package-to-backend flow rather than only checking shell syntax. The VM image does not provide a real `setxkbmap`, so this validates the integration boundary and argument propagation, not an actual desktop keyboard-state change. The test must be run on the provided HarmonyOS 6.0 VM; the current Windows-host run intentionally used a Linux target override and therefore does not count as OHOS evidence.

## Validation status

- Source archive download and SHA256 verification: passed.
- Recipe YAML/Python syntax and whitespace checks: passed.
- Windows-host Conan create with Linux target override: passed, 39 consumer assertions.
- HarmonyOS 6.0 x86_64 VM shell consumer: passed, 63 assertions; `/bin/sh`, `sha256sum`, all three helper scripts, and exactly five recorded `setxkbmap` backend flows executed successfully.
- The VM image does not provide Python 3 or Conan, so the OHOS-specific test is executed directly against the Conan-created package directory transferred with HDC; the Python Conan consumer remains the host-side Conan test.
- `ohc-run.py finish keyboards-rg 0.3-nmu2 built` was attempted. Its Conan package build reached the recipe, but the Windows host could not complete G0/W3 because the finish workflow expects the original source tarball and a zsh/Unix CI environment; `setup.sh` failed before targeted CI could run.
- The exact targeted CI command could not start because `zsh` is not installed on this Windows host. Running the same `ci/conan/build_and_test.sh` entry point through Git Bash reached CI setup but stopped because this host had no compatible `libsqlite3.so.0`/OHOS SQLite runtime; no local CI pass is claimed from that run.
- The full repository regression command reached `test_v1220.test_pf9` and failed on the host's temporary-git-repository setup with `FileNotFoundError [WinError 2]`; the package-specific checks and consumer tests passed independently.
- The package and both consumer paths are validated, but the repository finish/W3 result remains environment-blocked and is not represented as a successful CI result.
