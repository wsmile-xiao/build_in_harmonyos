# adns 1.6.0 adaptation notes

- Upstream source: `adns-1.6.0.tar.gz` (official chiark FTP, verified with `.sig` presence and SHA-256)
- Build system: Autotools
- Upstream regression inventory: 102 files matching `regress/case-*.sys`.
- Adaptation patch: keep generated regression harness sources in the out-of-source build directory.
- OHOS HMDFS fix: create Autoconf temporary directories with `umask 022` so `config.status` can write its generated AWK scripts.
- The build is serialized because the upstream generated regression harness omits complete parallel dependencies.
- Runtime coverage: IPv4 text/address conversion, port preservation, insufficient-buffer handling, invalid-address handling, and status-string lookup.
- Recipe note: the Windows-only `tool_requires("make/4.4.1")` carried over from the 1.6.2 recipe was removed. The OHOS/Linux build never consumes it (system GNU Make is used), and make/4.4.1 is not published in the ohpcd registry — the L0i registry probe for it failed (E477: CNB returns "system acceleration policy not enabled" for unpublished packages), blocking W3. Removing the dead conditional keeps the gate honest without weakening the OHOS build.

Final pass counts and current commit evidence are recorded in the PR after all validation gates complete.
---

**编译结束**: 2026-09-07 00:28
**最终状态**: built
