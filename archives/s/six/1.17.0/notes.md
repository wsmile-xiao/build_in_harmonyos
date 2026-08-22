# six 1.17.0 HarmonyOS adaptation notes

## Scope and classification

This archive packages six 1.17.0 for issue 2285. It is a B-class dependency
adaptation: the upstream project is one pure-Python module, has no runtime
dependencies, and requires no HarmonyOS patch.

## W0 dependency check

The PyPI metadata declares no runtime dependencies. The device-side command
`conan list "six/*" -r=ohpcd` returned no matching recipes, so this is the
bottom-level dependency needed by adapt 1.0.0.

## Source and build analysis

- Official sdist: `six-1.17.0.tar.gz`
- Source SHA256: `ff70335d468e7eb6ec65b95b99d3a2836546063f63acc5171de367e834932a81`
- Build metadata: setuptools with a distutils fallback
- Importable payload: `six.py`
- Upstream test file: `test_six.py`, with 201 collected pytest cases

Upstream explains that setuptools itself depends on six. The recipe therefore
does not invoke pip, setuptools, or distutils. It validates and copies `six.py`
directly to `lib/python/site-packages`.

## Test strategy

The full upstream pytest suite was run locally from the SHA256-verified sdist:
201 tests were collected, with 199 passed, 2 environment-dependent skips, and
0 failures. The Conan consumer test checks the resolved module path and
exercises public compatibility APIs, including text/binary conversion,
iterator helpers, metaclass helpers, and
`six.moves.urllib.parse`.

## Verification result

The isolated HarmonyOS aarch64 shadow CI run passed for this package only.
L0, L1, L4, and L5 passed; L2 skipped because six has no CLI. The L1e
destructive check removed the packaged `lib/` directory and confirmed that the
consumer test then failed, proving it does not use an ambient six installation.
See `reports/shadow-ci.md` for the frozen input and evidence hashes.

## Commands

Single-package verification:

```sh
CI_PACKAGES="archives/s/six/1.17.0" zsh ci/conan/build_and_test.sh
```

Shadow runner:

```sh
/path/to/run-ohos-shadow-ci.sh archives/s/six/1.17.0
```

After publication, unblock adapt with:

```sh
conan download "six/1.17.0" -r=ohpcd --only-recipe
```
