# uperf

uperf is a network performance tool originally developed at Sun Microsystems.
It measures unicast TCP/UDP transaction and throughput behavior between a
master and one or more slaves, driven by XML workload profiles (connect /
write / read / disconnect flowops, groups, transactions, statistics and
consistency reporting).

- Upstream: https://github.com/uperf/uperf
- License: GPL-3.0-or-later
- Adapted versions: `1.0.7/`

## Adaptation summary (1.0.7)

- Native OHOS build (device clang), `--disable-ssl --disable-sctp --disable-netstat`
  (musl lacks `netinet/sctp.h`; openssl not declared; netstat branch is
  Solaris-only).
- One portability patch: drop the `umask 077 &&` wrapper around the configure
  temp-dir creation (E011/HMDFS: `confXXXXXX/subs1.awk: Permission denied`).
- Upstream tests run for real inside `conan create`: the recipe starts the
  `uperf -s` slave around `make -C tests check` (the 1.0.7 tarball's test.sh
  does not start a slave; fixed later on master). Result: 21 PASS + 2 XFAIL
  of 23 registered cases; 10 conditional cases not registered, each declared.
- Consumer test: loopback slave+master transaction with 3 assertions.

See `1.0.7/notes.md` and `1.0.7/reports/` for details.
