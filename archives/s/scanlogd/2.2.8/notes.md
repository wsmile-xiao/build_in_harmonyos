# scanlogd 2.2.8 adaptation notes

## Status

Prepared and unverified. This sub-agent did not run an OHOS build or execute the
package on a HarmonyOS device.

## Source identity

- Upstream project: `https://github.com/openwall/scanlogd`
- Release tag: `SCANLOGD_2_2_8`
- Tagged commit: `18206eadfb4dac12372188839304a2317d31bf18`
- Official archive: `https://www.openwall.com/scanlogd/scanlogd-2.2.8.tar.gz`
- SHA256: `0bec45ecbcc8a9a3599cb38e21dcacf639ca3b33bb6973b20261315d065ea158`
- The extracted release tree compared byte-for-byte equal to the tagged Git tree.

## License

Upstream uses a heavily cut-down BSD-style license, identified by Debian as
`BSD~cut-down`. It is not BSD-2-Clause. This recipe records it as
`LicenseRef-Openwall-BSD-cut-down` rather than assigning a misleading SPDX
identifier.

## Build target and layout

The ordinary Makefile has no default build. Supported packet-capture targets
are `linux`, `libnids`, and `libpcap`. The recipe deliberately selects:

```text
make CC=clang linux -j1
```

This uses `socket(AF_INET, SOCK_RAW, IPPROTO_TCP)` from `in_linux.c` and does not
need libpcap or libnids. The upstream Makefile has no install target. Its RPM
spec installs the executable under `%_sbindir`, the man page under `man8`, and
`scanlogd.init` under `/etc/rc.d/init.d`.

The Conan package uses the tool layout:

```text
bin/scanlogd
etc/scanlogd.init
share/man/man8/scanlogd.8
share/doc/scanlogd/README.md
licenses/LICENSE
```

The archived init script is provided as an upstream service-control reference.
It depends on Owl/SysV `functions` and is not enabled automatically.

## OHOS compatibility investigation

- No libpcap dependency is introduced by the selected backend.
- The source uses standard Linux/musl headers (`sys/socket.h`, `netinet/ip.h`,
  `netinet/tcp.h`, `pwd.h`, `grp.h`, and `syslog.h`).
- The program requires raw-socket capability. It exits with status 1 when the
  socket cannot be created.
- One source patch adds `--help`, `--version`, and unknown-option handling.
  It lets packaging and validation tooling inspect the daemon without entering
  the privileged capture path; packet processing and capture behavior remain
  unchanged.

A host-only sanity build with GCC succeeded:

```text
cc -Wall -O2 -fomit-frame-pointer -c scanlogd.c
cc -Wall -O2 -fomit-frame-pointer -c in_linux.c
cc -s scanlogd.o in_linux.o -o scanlogd
```

An unprivileged host invocation with no arguments exited 1 with:

```text
socket: Operation not permitted
```

This is Linux host evidence only, not OHOS or device evidence.

## Upstream tests

There is no tests directory and no `test` or `check` target in the Makefile.
The upstream result is therefore declared as **0/0**, not inferred from the
consumer checks.

## Consumer checks

`test_package/test.sh` intentionally does not claim packet-capture success. It
checks the installed executable, man page, and init template, verifies the
new `--help`, `--version`, and unknown-option contracts, then verifies that an
unprivileged no-argument invocation follows the raw-socket startup path and
fails with exit status 1 plus a permission error.

If the test runs as root, the permission assertion is reported as SKIP rather
than PASS. It is skipped because the package cannot safely prove capture startup
without real traffic in ordinary CI.
