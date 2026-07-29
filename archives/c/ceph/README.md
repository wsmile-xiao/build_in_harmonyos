# Ceph

Ceph is a distributed storage platform. The HarmonyOS PC recipe currently
packages the portable CRUSH data-placement core as a static C library.

## HarmonyOS PC Adaptation

- Builds the CRUSH C sources without Ceph daemons, RADOS clients, or
  `crushtool`.
- Provides portable fixed-width integer aliases instead of Linux UAPI headers.
- Exposes the installed library as the CMake target `ceph::crush`.
- Runs adapted upstream CRUSH scenarios and a package-consumer integration
  test.

## Upstream

- Homepage: https://ceph.io/
- Source: https://github.com/ceph/ceph
