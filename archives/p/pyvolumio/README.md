# pyvolumio

pyvolumio is a pure Python library that provides an async interface to control
[Volumio](https://volumio.org/) media players over the local network REST API.

## Package contents

- Public Python package: `pyvolumio`
- Public API: `Volumio`, `CannotConnectError`
- License: MIT

## OpenHarmony adaptation

- Packages the architecture-independent Python sources via `pip --prefix`.
- Vendors the runtime dependency `aiohttp` into package `site-packages`.
- Upstream ships no official test suite; recipe runs an offline smoke in
  `build()` and a mock-session consumer test in `test_package/`.
- Requires no source patch.

## Usage

```python
from pyvolumio import Volumio

v = Volumio("192.168.1.10", 3000)
# info = await v.get_system_info()
# await v.play()
assert v.canonic_url("/albumart") == "http://192.168.1.10:3000/albumart"
```

Upstream: https://github.com/OnFreund/PyVolumio
