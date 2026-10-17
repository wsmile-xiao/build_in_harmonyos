# SDL2_net

SDL2_net is the official SDL2 networking companion library. It provides a
small portable API for TCP, UDP, address resolution, packet allocation, and
socket readiness sets.

## Version

- `2.2.0`

## Dependency

- Exact Conan dependency: `sdl2/2.30.10`
- SDL2 minimum accepted by upstream: `2.0.4`
- The `shared` option must match between SDL2 and SDL2_net.

## OpenHarmony PC Adaptation

- Build with upstream CMake.
- Set `SDL2NET_INSTALL=ON` and `SDL2NET_SAMPLES=OFF` explicitly.
- Export `SDL2_net::SDL2_net` for shared packages and
  `SDL2_net::SDL2_net-static` for static packages.
- On `OHOS|HarmonyOS`, skip upstream shared-library version aliases and install
  one real unversioned `libSDL2_net.so`; retain upstream behavior elsewhere.
- On native OHOS, atomically sign the shared library and every test executable
  and verify one nonempty `.codesign` section before execution.
- Do not carry the historical `config.guess` or `config.sub` patches; they are
  only relevant to the unused Autotools path.
- Validate TCP and UDP only over the local loopback interface.

An SDK 12 CMake install reproduced a collision between upstream version links
and its extra unversioned link. The scoped CMake patch passed fresh shared and
static install plus installed-metadata compile/link preflight. Fresh W3 must
still verify the actual file, SONAME, NEEDED, RPATH, and runtime contract.

## Status

The r27 target run completed against the frozen, independently validated SDL2
r30 package trees: the upstream entry passed `1/1`, the six adapted entries
passed `6/6`, and both shared and static modes executed `7/7`. The separate W0
release-chain gate remains blocked until the exact SDL2 recipe can be freshly
consumed as a published artifact; that publication gate does not change the
completed target test status.
