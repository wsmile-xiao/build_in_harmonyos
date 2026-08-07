# adns 1.6.2 adaptation notes

- Upstream source: `adns-1.6.2.tar.gz`
- Build system: Autotools
- Upstream regression inventory: 102 files matching `regress/case-*.sys`.
- Adaptation patch: keep generated regression harness sources in the out-of-source build directory.
- OHOS HMDFS fix: create Autoconf temporary directories with `umask 022` so `config.status` can write its generated AWK scripts.
- The build is serialized because the upstream generated regression harness omits complete parallel dependencies.
- Runtime coverage: IPv4 text/address conversion, port preservation, insufficient-buffer handling, invalid-address handling, and status-string lookup.

Final pass counts and current commit evidence are recorded in the PR after all validation gates complete.
