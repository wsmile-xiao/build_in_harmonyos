# libslirp 4.9.3 test report

## Upstream inventory

The official `v4.9.3` source registers exactly two Meson integration tests.
Optional fuzz executables are build targets and are not counted as `test()`
entries.

| Test | Type | Official host | Patched HarmonyOS |
|---|---|---:|---:|
| `ping` | integration | NOT RUN | PASS on both fresh runs |
| `ncsi` | integration | NOT RUN | PASS on both fresh runs |

No native-host result from an older version is reused for 4.9.3.

## Added consumer

One installed-package integration flow is declared in
`test_package/test_package.c`. It materially checks the runtime version,
creates a real `Slirp` context, exercises state and poll APIs, validates
callback cleanup, and exits nonzero on failure.

| Flow | Official host | Patched HarmonyOS |
|---|---:|---:|
| installed-package consumer | NOT RUN | PASS on both fresh runs |

## Target runs

The fallback-device r3 run exercised the skill-owned `finish` flow. Its G2
and embedded W3 stages each performed a real `conan create`. The W3 stage
passed both upstream tests (`2/2`, `Fail: 0`) and the consumer (`1/1`). The
skill generated `.ci-result.json` with `step=W3_local_ci`, exit code 0, and
integrity value `9d52fd260fb65860`.

The frozen r3 evidence is bound by:

- input archive SHA-256:
  `7ca885bdff2ba676b0ea1e328e1314dd186a87dce9598b97c7cbb654b05fc4ba`;
- G2 Conan log: 26,907 bytes, SHA-256
  `9b1468d8641a1344cca905dcd557ac9c4328d34f9358fa534b11ee4df92ade8d`;
- W3 Conan log: 23,107 bytes, SHA-256
  `92aa17bb14714a6248230709c65ed8ce060e4ae54b11a32421655c279f72a494`;
- `.ci-result.json` SHA-256:
  `41a9d3d215b85a0deb2d5715eedcdb14f1ac56f423679b2362b71f96300a1d14`;
- evidence bundle SHA-256:
  `34254c2ede3bacd9100c4e69238515da54d5ecd463d24ae293ad298274107664`.

The primary-device r4 run independently executed the standard
`ci/conan/build_and_test.sh` pipeline and returned 0. It passed L0, L1, L4,
and L5; the L1 destructive reverse test also proved that the consumer fails
when the package library and headers are removed. The same run passed the two
upstream tests and the installed-package consumer.

The frozen r4 evidence is bound by:

- complete pipeline log: 26,396 bytes, SHA-256
  `074edbf97fd7c4cfb915881a5d7e7a43e1a10944245afb74bb4f1981c0dd5f74`;
- Conan log: 24,360 bytes, SHA-256
  `f930d808f4ff639b241fffb01a5d864011966749d6b0ea05b1a85b37205e2114`;
- evidence bundle SHA-256:
  `fa70010e0f983d31b96b567c4bde91d88c466e5caf4a2f044d753de8ed842d3a`.

## Artifact contract and accounting

Both devices produced the same 1,038,912-byte `libslirp.so`, SHA-256
`eeceed68e1637b31da93899a0c5048f8d5ca4b1d9a021c34698e6db2fc47acc7`.
The ELF is 64-bit little-endian, type `ET_DYN`, machine `EM_AARCH64`. Each
package contains one real unversioned shared object, no library symlink, and
exactly one `.codesign` section.

Independent adapted flows are `3/3`: two unchanged upstream entries plus one
installed-package consumer. Repeated G2/W3 runs, signing operations, and
internal assertions are supporting checks and are not counted as additional
tests. Official current-HEAD CI remains pending.
