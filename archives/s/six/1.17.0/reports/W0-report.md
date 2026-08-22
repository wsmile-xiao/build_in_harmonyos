# six 1.17.0 W0 report

## Identity

- Library: `six`
- Version: `1.17.0`
- Issue: `2285`
- Classification: B-class dependency
- Worktree branch: `feat/six-1.17.0-2285`
- Upstream project: `https://github.com/benjaminp/six`

## Source

- PyPI sdist URL: `https://files.pythonhosted.org/packages/source/s/six/six-1.17.0.tar.gz`
- SHA256: `ff70335d468e7eb6ec65b95b99d3a2836546063f63acc5171de367e834932a81`
- Build system: setuptools with distutils fallback
- Package shape: single pure-Python module, `six.py`

## Dependency result

six has no runtime dependencies. The HarmonyOS device query
`conan list "six/*" -r=ohpcd` returned no recipes, confirming that this package
is a new bottom-level dependency adaptation.

## Test inventory

The sdist includes `test_six.py`. Pytest collected 201 parameterized cases from
the unmodified upstream file: 199 passed, 2 were skipped by environment
conditions, and 0 failed. The Conan test package additionally provides a
dependency-free consumer test against the installed package.

## W0 result

PASS. No missing lower-level dependency blocks recipe preparation or shadow CI.
