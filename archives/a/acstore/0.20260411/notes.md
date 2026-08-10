# acstore 0.20260411 adaptation notes

- Upstream: `https://github.com/log2timeline/acstore`, tag `20260411`.
- Source archive SHA256: `0be32cc0b0c1e333f3b6516bfa9bd1afc72b5f56517191a2a1ca57422b9bfc1d`.
- Build system: Python `setuptools`/`pyproject.toml`.
- Runtime dependency declared by upstream: `PyYAML >= 3.10`; it is installed
  into the isolated package tree by pip during the Conan build.
- The consumer test calls `YAMLAttributeContainerDefinitionsFile._ReadDefinition`
  and asserts the resulting container type and schema.
- This package is Python despite the task list's C++ classification; no C++
  compiler is needed by the upstream project.

## Upstream setuptools packaging bug (fix by patch)

The upstream `pyproject.toml` declares:

    [tool.setuptools.packages.find]
    where = ["."]
    include = ["acstore"]

The non-glob `include = ["acstore"]` matches only the top-level `acstore`
package and silently drops the `acstore.helpers` and `acstore.containers`
subpackages from the built wheel. As a result `from acstore.helpers import
...` fails after `pip install` (ModuleNotFoundError).

The recipe patches this with `patches/0001-pyproject-find-glob.patch`:

    -include = ["acstore"]
    +include = ["acstore*"]

The glob form causes setuptools to discover and package both subpackages.

## package_type

acstore is a pure-Python importable module with a runtime PyYAML dependency
and no C/C++ compilation step. Consumers `import acstore`, so the package is
a Conan `library` (not an `application`). This matches the repo convention
for importable Python modules (e.g. argon2, aws-c-common).

## Real on-device verification (2026-08-09)

- Host: Linux aarch64, Python 3.12.9, Conan 2.29.1.
- `git apply --check patches/0001-pyproject-find-glob.patch` on a fresh
  extraction of the tag 20260411 source: exit 0.
- `conan create archives/a/acstore/0.20260411 --build=missing`: built and
  packaged 31 `.py` files plus the PyYAML C extension, including the
  `acstore/helpers` and `acstore/containers` subpackages.
- Upstream tests `python3 run_tests.py` (run from the unpacked source root
  with PyYAML installed): **Ran 62 tests in 0.093s — OK**. All 62 passed,
  0 failed, 0 skipped.
- test_package `python3 test_acstore.py`: `acstore smoke test: YAML
  definition API assertions passed`.
