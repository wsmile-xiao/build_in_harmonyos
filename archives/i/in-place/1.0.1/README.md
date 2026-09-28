# in-place 1.0.1 for OpenHarmony PC

`in_place` is a pure-Python module that lets a program read and rewrite a file at the same path while handling temporary files. The upstream package requires Python 3.8 or newer and is distributed under the MIT license.

## Package contents

The Conan package installs `python/in_place/` and `licenses/LICENSE`. It contains no native library or executable. Conan's consumer run environment adds the package's `python/` directory to `PYTHONPATH`.

In a Conan consumer that requires `in-place/1.0.1`, use the upstream API:

```python
import in_place

with in_place.InPlace("somefile.txt") as stream:
    for line in stream:
        stream.write("".join(char for char in line if char not in "AEIOUaeiou"))
```

The upstream source and its test suite are available at [jwodder/inplace](https://github.com/jwodder/inplace). The Conan recipe packages the existing `src/in_place` module directly; it does not run the upstream Hatch build backend.

## Verification scope

OpenHarmony H1 evidence is summarized in [`reports/test-report.md`](reports/test-report.md). The upstream suite ran on the fixed source archive in H1-002; Conan and W3 package/consumer checks ran in H1-005. These local target results do not represent official remote CI or contest acceptance. The contest task's language label is `cpp`, while the upstream source is Python; that eligibility mismatch remains disclosed.
