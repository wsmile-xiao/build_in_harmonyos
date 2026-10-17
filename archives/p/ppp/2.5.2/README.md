# ppp 2.5.2 for OpenHarmony

This directory contains the reproducible Conan adaptation prepared for issue
`#2118`. It replaces the legacy binary-archive notes with a source build from
the official upstream 2.5.2 release tarball.

## Scope

- Build system: GNU Autoconf/Automake/Libtool (generated `configure` included).
- Required library: `openssl/3.5.6` for EAP-TLS, PEAP, MS-CHAP and MPPE.
- Installed commands: `pppd`, `chat`, `pppstats`, `pppdump`,
  `pppoe-discovery`.
- Installed plugin: `lib/pppd/2.5.2/pppoe.so` plus the other upstream
  default plugins.
- Disabled optional integrations: external libatm, PAM, PCAP activity filters,
  SRP, systemd notifications and multilink/TDB. PPPoATM retains upstream's
  built-in ATM address parser fallback.

The OHOS tuple is forced to `aarch64-unknown-linux-ohos`, which produces
`host_os=linux-ohos` and selects upstream's Linux user-space implementation.

## Validation status

- The complete W0 graph resolves to the published `openssl/3.5.6` package.
- The official source archive was downloaded and its SHA-256 was verified.
- Conan 2.29.1 applies all seven patches to a clean official source tree; Python,
  YAML, patch-manifest, L4 static scan and change-scope checks pass locally.
- Single-package OHOS shadow CI passes on a HarmonyOS aarch64 device: upstream
  `make -j1 check` reports 5/5 passed, the Conan package and test package pass,
  and `pppd --version` prints `pppd version 2.5.2`.

PPPoE runtime operation additionally requires compatible kernel support and
privileged access. The test package deliberately limits itself to installed
artifact checks and `pppd --version`; it does not open `/dev/ppp`, alter routes
or create a network connection.
