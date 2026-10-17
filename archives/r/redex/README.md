# redex

Redex is an Android bytecode optimizer from Meta.

## HarmonyOS PC adaptation

The `2026.04.30` recipe builds the native `redex-all` optimizer for
HarmonyOS PC aarch64 and packages the upstream `redex.py` driver and
`pyredex` modules in the same `bin` directory.

The dependency closure is exact:

- `boost/1.91.0.1.1`, including the compiled components required by Redex;
- `jsoncpp/1.9.8`;
- `zlib-ng-compat/2.3.3`.

Redex is packaged as an application, not as a selectable shared/static
library. The executable consumes the published shared Boost and JsonCpp
packages, while the upstream build's `redex`, `tool`, and `resource` helper
libraries remain static archives inside the package.

The CMake build is the product packaging path. The authoritative upstream
test denominator is discovered separately from the Autotools runner and each
GoogleTest executable's leaf inventory; CMake does not register the complete
upstream suite.
