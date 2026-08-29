# recode 3.7.15 HarmonyOS PC device test

## Scope

- Target: HarmonyOS PC AArch64 device.
- Source: recode `v3.7.15` formal Conan package build.
- Test command:

  ```sh
  cd <device-test-dir>/tests
  RECODE=<formal-package>/bin/recode \
  LD_LIBRARY_PATH=<formal-package>/lib \
  PYTHONPATH=<device-test-dir>/tests \
  python3 ./pytest -v ./t*.py
  ```

- The real AArch64 `recode` ELF and `librecode.so.3` were signed in place at
  their final device test paths before execution.

## Result

The unmodified upstream test modules and `pytest` harness executed 496 tests
on the HarmonyOS PC AArch64 target:

| Result | Count |
| --- | ---: |
| Passed | 496 |
| Failed | 0 |
| Total | 496 |

- The previously failing `t70_inferenz.py/test_1` passed after linking the
  package against Conan `libiconv/1.17`.

All tests passed, including the Java conversion tests and both
`t90_bigauto.py` cases. The target CLI also passed `--version` and a basic
conversion smoke test.

## Test adapter boundary

The generated test Makefile references a host Python executable, and the
target Python Cython extension was not available. Therefore the upstream
test modules and harness were executed with a device-only `Recode.py` facade
that invokes the final packaged `recode` CLI. This facade and the deployment
copy are not source changes in the PR. The result is target execution evidence
for the CLI-backed upstream tests.

## Evidence

- Formal Conan log SHA256:
  `9e18111278c68f12b2a48aa9b64befef137718bc7f97da6919abcc4f1526489a`
- Targeted test log SHA256:
  `ce49700288645805c19819a976a0b24c1616e1db8a42c4458cc31d3d5c82916d`
- Full upstream test log SHA256:
  `041440e2b3e58ac8521e32cb6c6682b575d636f208f0fc0835e9d6d527f90dba`
- Final packaged `recode` SHA256:
  `6cd78210728b7f0b3bf1c99de9afe0dca2ad74d20385dd5ad0c0eb805e748a10`
- Final packaged `librecode.so.3.7.15` SHA256:
  `7f260cc4a5343c15eaaffdd785660944cabd88861eca349c49f42744269bd20d`

The device test does not cover CI, review, merge, or remote package
publication.
