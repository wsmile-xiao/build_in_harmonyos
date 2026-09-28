# zict 3.0.0 HarmonyOS PC port

zict is a pure-Python mutable-mapping library. Its sdist has no runtime dependencies and no native extension. The recipe installs the upstream package into `lib/pythonX.Y/site-packages` and exports that directory through Conan's run and build environments.

The recipe executes the upstream pytest suite on the HarmonyOS AArch64 device. The default pytest temporary root fails on the device's FUSE-backed `/storage` mount with an ownership check, so the runner supplies a task-local `--basetemp`. Existing knowledge draft `E543-draft-DF80` already records this reusable pytest runner workaround; this port does not duplicate it as a Path B submission.

The suite's `test_stress_different_keys_threadsafe` can starve a peer on a single-CPU runner. The recipe carries the corresponding upstream fix from commit `b142286c09bddd27cba29e0cfb968cfc0ed54233`, limited to the test helper. Runtime package code is unchanged by this patch.

Upstream test command: `python3 -m pytest -o addopts= --timeout=180 --timeout-method=signal --basetemp=<build-folder>/pytest-tmp zict/tests`.

The consumer test imports the packaged `zict` module and verifies its version, LRU lookup and eviction behavior, and that the import resolves from the package's site-packages directory.

On the HarmonyOS AArch64 device (CPython 3.14.7), `conan create` exited 0. The upstream suite collected 522 cases and passed 522/522; the optional LMDB test module was skipped at collection because the `lmdb` binding is unavailable. The Conan consumer test passed all five checks.
