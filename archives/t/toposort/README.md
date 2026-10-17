# toposort

`toposort` is a pure-Python library that orders hashable objects according to
their dependency graph. The package has no runtime dependencies.

The OpenHarmony Conan package installs the upstream `toposort.py` module under
`lib/python` and adds that directory to `PYTHONPATH` for Conan consumers.
With Conan 2.29, consumers should request the runtime environment explicitly:

```python
def requirements(self):
    self.requires("toposort/1.10", run=True)
```
