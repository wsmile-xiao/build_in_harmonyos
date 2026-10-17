# itypes

`itypes` provides basic immutable container types for Python, including `Dict`
and `List`. Nested values are coerced to immutable containers, and updates
return new copies.

```python
import itypes

items = itypes.Dict({"name": "Ada", "tags": ["compiler", "math"]})
updated = items.set("name", "Grace")
```

The OpenHarmony PC Conan package installs the module at `lib/python/itypes.py`.
To use an installed package, include its `lib/python` directory in
`PYTHONPATH`, then import `itypes` as usual. The package contains pure Python
code and has no native compilation step.

The Conan recipe and consumer tests are validated through the project's
`conan create` workflow. Distribution uses the Conan release pipeline.

Upstream project: https://github.com/PavanTatikonda/itypes
