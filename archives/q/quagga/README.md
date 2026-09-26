# quagga — GNU Quagga routing daemon suite

GNU Quagga is a free routing software suite implementing the TCP/IP routing
protocols BGP4+/RIPng (IPv6), BGP4+/RIP/OSPFv2/IS-IS/PIM-SM (IPv4), plus the
`zebra` routing-information-base daemon that owns the kernel routing table,
the integrated `vtysh` shell and `watchquagga`.

- **Homepage**: https://github.com/Quagga/quagga
- **License**: GPL-2.0-or-later
- **Category**: networking
- **Upstream status**: upstream stopped in 2018 (forked as FRRouting); 1.2.4 is
  the last release tag.

## Available Versions

| Version | Status | Notes |
|---------|--------|-------|
| 1.2.4   | built  | path A stock minimal build |

## OHOS Platform Adaptations (1.2.4)

- **bootstrap**: the GitHub tag tarball ships only `configure.ac` (no
  `configure`, no `config.guess`), so the recipe runs `autoreconf -fi` with
  `tool_requires("automake/1.18")` + `tool_requires("libtool/2.5.4")`.
- **E007**: `config.guess` rewritten after bootstrap — `uname -s` returns
  `HarmonyOS`, which the GNU script does not recognise.
- **E091**: `-D__MUSL__` added — OHOS' `<linux/socket.h>` (pulled in by
  `<linux/netlink.h>`/`<linux/rtnetlink.h>`) re-defines `struct
  sockaddr_storage` against musl' s `<sys/socket.h>`; zebra's netlink face
  cannot compile without it.
- **HMDFS**: `umask 077` -> `umask 022` in generated `configure`/`config.status`.
- **runtime identity**: `--enable-user/--enable-group/--enable-vty_group` point
  at `root` because OHOS has no `quagga:quagga` account.
- **netlink face**: measured working — `socket(PF_NETLINK, SOCK_RAW,
  NETLINK_ROUTE)` succeeds and a real `RTM_GETROUTE` dump returns data on the
  HarmonyOS PC as an unprivileged user (details in `1.2.4/notes.md`).
- **vtysh / nhrpd off**: `--disable-vtysh` and `--disable-nhrpd`, see
  *Binaries* below for the measured publication probes and what they cost.

## Binaries

`zebra`, `bgpd`, `ripd`, `ripngd`, `ospfd`, `ospf6d`, `isisd`, `pimd`,
`watchquagga` (ELF 64-bit aarch64, musl libc).

- **vtysh is not built** (`--disable-vtysh`): it is the single component that
  requires libreadline — `configure.ac:757-761` aborts the configure when
  `AC_CHECK_LIB(readline, main)` fails, and none of the four termcap probes
  (termcap/tinfo/curses/ncurses) found `tputs` in this sysroot.  The readline
  recipes for 8.2/8.3 do live on `origin/main`, but the exact-binary probe
  `conan install --requires=readline/8.3@ohpcd/stable --build=never` answers
  `Unable to find ... in remotes` (8.2 likewise), i.e. a publication gap rather
  than an adaptation gap.  What is switched off is the *interactive front-end
  only*: the routing daemons and their netlink face remain built and tested.
- **nhrpd is not built** (`--disable-nhrpd`): `configure.ac:1348` runs
  `PKG_CHECK_MODULES([CARES], [libcares])` for nhrpd only, and configure aborts
  with `No package 'libcares' found` (measured, W3 round 5).  The c-ares recipes
  for 1.34.4/1.34.5/1.34.6 are on `origin/main`, yet
  `conan install --requires=c-ares/1.34.6@ohpcd/stable --build=never` answers
  `Unable to find 'c-ares/1.34.6@ohpcd/stable' in remotes` (1.34.5 likewise) —
  the same publication gap.  NHRP (RFC 2332) is an NBMA overlay protocol used
  with mGRE/ipsec; BGP/OSPF/RIP/IS-IS/PIM and zebra keep working.

