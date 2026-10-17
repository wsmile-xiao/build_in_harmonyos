# vincenty

vincenty is a pure Python implementation of Vincenty's inverse formula. It
calculates the distance between two latitude/longitude points on the WGS 84
ellipsoid in kilometres or miles.

## Package contents

- Public Python package: `vincenty`
- License: Unlicense

## OpenHarmony adaptation

- Packages the architecture-independent Python source directly under
  `lib/python/site-packages`.
- Runs all 9 doctest examples embedded in the official `0.1.4` source.
- Runs a separate 14-assertion consumer test against the packaged module.
- Requires no patch and no Conan package dependency.

## Usage

```python
from vincenty import vincenty

boston = (42.3541165, -71.0693514)
new_york = (40.7791472, -73.9680804)
assert vincenty(boston, new_york) == 298.396057
assert vincenty(boston, new_york, miles=True) == 185.414657
```

Upstream: https://github.com/maurycyp/vincenty
