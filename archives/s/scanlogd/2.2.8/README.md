# scanlogd 2.2.8

`scanlogd` is Openwall's TCP port scan detector. It writes one syslog alert per
detected scan and needs privileged access to a packet-capture interface.

This candidate uses the upstream Linux raw-socket backend
(`make linux`), so it does not require libpcap or libnids. The packaging
installs:

- `bin/scanlogd`
- `etc/scanlogd.init`
- `share/man/man8/scanlogd.8`
- `share/doc/scanlogd/README.md`
- `licenses/LICENSE`

The portability patch adds standard non-interactive `--help` and `--version`
handling and rejects unknown options before daemon startup. A no-argument run
still follows the upstream raw-socket initialization path, so an unprivileged
run exits 1 with a `socket:` permission error. Running the daemon successfully
requires the appropriate raw-socket capability and the upstream `scanlogd`
user/chroot setup described in the manual page.

Status is `prepared / unverified`; no HarmonyOS device result is claimed here.
