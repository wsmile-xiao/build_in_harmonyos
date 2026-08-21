# adapt 1.0.0 HarmonyOS adaptation notes

## Scope

This archive prepares the MycroftAI Adapt Intent Parser (`adapt-parser` on
PyPI) for Conan consumption.  The upstream source is the Git tag
`release/v1.0.0`, commit `6cac0e499a586fda160f5252c52272cc822912bb`.

## W0 dependency check

The upstream `requirements.txt` contains `six>=1.10.0`. No `six` recipe or
archive is present in this branch. Per the one-library/one-PR rule, this PR
does not add or vendor a six adaptation. The independent six adaptation is
tracked by issue #2285 and PR #5809
(`https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/5809`);
the PR is open and has not been published to `ohpcd`. The device shadow test
used its preinstalled `six 1.17.0`; publish six separately before treating
adapt as independently reproducible from the `ohpcd` registry.

## Recipe design

- Build system: setuptools (`setup.py`), pure Python; no C/C++ compiler is
  required.
- `build()` copies the pure Python modules to a staging directory without
  invoking pip or setuptools, so Conan does not silently fetch dependencies.
- `package()` installs modules under `lib/python/site-packages`;
  `package_info()` exports that directory through `PYTHONPATH`.
- The consumer test registers two entities, builds an `IntentBuilder`, and
  verifies the parsed intent and confidence from the installed package.

## Local verification

The source archive URL, SHA256, and recipe syntax were verified locally. The
complete upstream suite was run from the verified source archive by expanding
the same eight files used by `run_tests.sh test` (the files use non-standard
pytest names):

```text
pytest test/ContextManagerIntegrationTest.py test/ContextManagerTest.py \
  test/DomainIntentEngineTest.py test/EntityExpanderTest.py \
  test/EntityTaggerTest.py test/IntentEngineTest.py test/IntentTest.py \
  test/TrieTest.py -q
76 passed in 0.24s
flake8 adapt test --select=E9,F63,F7,F82 --show-source
exit 0
```

The suite contains eight test modules and 76 pytest cases; no upstream test
file was modified. The local interpreter was Python 3.12.10 and the isolated
test environment used six 1.17.0. The OHOS device provides Python 3.12.9 and
six 1.17.0. Conan verification was performed through the isolated device
shadow runner and passed.

## Shadow CI result

The isolated single-package run passed on the HarmonyOS aarch64 device with
Python 3.12.9 and six 1.17.0. L0, L1, L4, and L5 passed; L2 skipped because
this pure Python library has no CLI. L1e removed `lib/` and confirmed the
consumer test then failed, proving it uses the packaged modules. See
`reports/shadow-ci.md` for the run directory and evidence hashes.

## Next commands

After adapting and publishing `six`, run the isolated package verification:

```sh
conan download "six/1.17.0" -r=ohpcd --only-recipe
CI_PACKAGES="archives/a/adapt/1.0.0" zsh ci/conan/build_and_test.sh
```

For the OHOS device or shadow runner, queue only this package after `six` is
available and use the project runner's single-package command, for example:

```sh
/path/to/run-ohos-shadow-ci.sh archives/a/adapt/1.0.0
```
