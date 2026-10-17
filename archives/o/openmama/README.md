# OpenMAMA

OpenMAMA is the middleware agnostic messaging API (MAMA) from FINOS: a C API and
C++ / MAMDA layers sitting on top of pluggable middleware bridges, together with
the tooling that upstream ships for testing and benchmarking a deployment.

## HarmonyOS PC Adaptation

The recipe packages the reusable, middleware independent part of OpenMAMA:

- `libmama` / `libmamacpp` / `libmamda` and their static counterparts
- `libwombatcommon` and `libwombatcommoncpp` (portability and utility layer)
- the base bridge (`libmamabaseimpl`) that real bridges are built on, the stub
  bridge (`libmamanoopimpl`), the OpenMAMA Playback bridge, the data quality
  plugin and the noop entitlement bridge
- public headers under `include/{mama,mamda,wombat}`, `config/mama.properties`
  and the upstream example/test tools in `bin/`

The AMQP bridge and its payload bridge are cropped: they are the only consumers
of qpid-proton, which is not available for this platform. The consequences are
documented and asserted by the package tests - there is no working middleware in
the package, so `mama_open()` reports `MAMA_STATUS_NO_BRIDGE_IMPL` until a
payload bridge is added.

## Upstream

- Source: https://github.com/finos/OpenMAMA
- Release used here: tag `OpenMAMA-6.3.2-release`
