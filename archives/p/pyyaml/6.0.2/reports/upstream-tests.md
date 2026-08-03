# Upstream Test Report: PyYAML 6.0.2

## Scope

- Source: official PyPI sdist for PyYAML 6.0.2.
- Test entry: `tests/legacy_tests/test_all.py`.
- Environment: pure Python, `PYYAML_FORCE_LIBYAML=0`.
- Optional LibYAML extension tests are out of scope because this adaptation does
  not build `yaml._yaml`.

## Result

- Pure-Python upstream cases: `1283/1283` passed.
- Skipped optional LibYAML extension cases: not counted in the package result.
- HarmonyOS PC device run: `1283/1283` pure-Python upstream cases passed
  before packaging; the packaged consumer test then passed.

## Command

```sh
PYTHONPATH="$PWD/lib:$PWD/tests/legacy_tests" \
PYYAML_FORCE_LIBYAML=0 \
PYTHONDONTWRITEBYTECODE=1 \
python tests/legacy_tests/test_all.py
```
