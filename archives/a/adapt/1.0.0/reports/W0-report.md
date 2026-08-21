# adapt 1.0.0 W0 report

## Identity

- Library: `adapt`
- Upstream distribution: `adapt-parser`
- Version: `1.0.0`
- Issue: `2282`
- Worktree branch: `feat/adapt-1.0.0-2282`
- Upstream tag: `release/v1.0.0`
- Upstream commit: `6cac0e499a586fda160f5252c52272cc822912bb`

## Source

- URL: `https://github.com/MycroftAI/adapt/archive/refs/tags/release/v1.0.0.tar.gz`
- SHA256: `a5e122ae27437b9dec932ff6470463bb734e909e45e02b672fc47afdeed2861c`
- Build system: setuptools (`setup.py`)
- Package shape: pure Python modules under `adapt/`

## Dependency result

`requirements.txt` declares `six>=1.10.0`. The current adapt branch does not
contain a six recipe. The independent six adaptation is tracked by issue #2285
and PR #5809:
`https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/5809`.
The PR is open and has not yet been published to `ohpcd`. The passing shadow
test used the device's preinstalled `six 1.17.0`, so adapt must be rerun after
six is published.

## Checks completed

- Upstream tag and commit resolved with `git ls-remote`.
- Source archive downloaded and SHA256 matched the recorded value.
- Upstream file inventory confirms `setup.py`, `run_tests.sh`, and eight test
  modules.
- Conan recipe, source metadata, consumer test, manifest, and notes prepared.
- The complete upstream test set was executed from the verified archive by
  expanding the eight files named by `run_tests.sh test`: `76 passed in
  0.24s`. The official flake8 gate passed with exit code 0.
- Isolated single-package shadow CI passed on the HarmonyOS aarch64 device.
- L1e destructive verification confirmed the consumer test requires the
  packaged `lib/python/site-packages/adapt` modules.

## Remaining publication item

Merge and publish `six` independently, then rerun adapt before treating `adapt` as reproducible
from the `ohpcd` registry alone.
