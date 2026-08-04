# pysmappee

pysmappee is the official pure Python library wrapping the
[Smappee](https://www.smappee.com/) cloud/local REST API (v3) and MQTT interface.
It is used as a dependency by the Home Assistant Smappee integration.

## Package contents

- Public Python package: `pysmappee`
- Public API: `Smappee`, `SmappeeApi`, `SmappeeLocalApi`
- License: MIT

## OpenHarmony adaptation

- Packages the architecture-independent Python sources via `pip --prefix`.
- Vendors runtime dependencies (`cachetools`, `paho-mqtt`, `pytz`, `requests`,
  `requests-oauthlib`, `schedule`) into package `site-packages`.
- Upstream ships no official test suite (`test/` is an empty placeholder);
  recipe runs an offline smoke in `build()` and a consumer test in
  `test_package/`.
- Requires no source patch.

## Usage

```python
from pysmappee import Smappee
from pysmappee.api import SmappeeApi
from pysmappee.helper import urljoin, is_smappee_energy

assert urljoin("https://a.com/", "b", "c") == "https://a.com/b/c"
assert is_smappee_energy("100123")

api = SmappeeApi(client_id="...", client_secret="...", farm=1)
wrapper = Smappee(api=api, serialnumber=None)
```

Upstream: https://github.com/smappee/pysmappee
