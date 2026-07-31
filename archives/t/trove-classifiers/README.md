# trove-classifiers

trove-classifiers is the canonical, typed Python data source for classifiers
accepted by the Python Package Index.

## Package contents

- Public Python package: `trove_classifiers`
- Type marker: `py.typed`
- Command: `trove-classifiers`
- License: Apache-2.0

## OpenHarmony adaptation

- Packages the architecture-independent Python sources directly.
- Runs all 18 upstream pytest cases from the official source distribution.
- Runs a separate 24-assertion consumer test against the packaged API and CLI.
- Requires no source patch and no Conan runtime dependency.

## Usage

```python
from trove_classifiers import classifiers, deprecated_classifiers

assert "Programming Language :: Python :: 3" in classifiers
assert "Natural Language :: Ukranian" in deprecated_classifiers
```

The `trove-classifiers` command prints all current classifiers in sorted order.

Upstream: https://github.com/pypa/trove-classifiers
