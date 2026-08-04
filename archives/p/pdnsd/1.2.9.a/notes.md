# pdnsd 1.2.9.a adaptation notes

## Source

- Upstream home page from README: `http://members.home.nl/p.a.rombouts/pdnsd/`
- Original release host is no longer reachable from this environment.
- GitHub mirror `kwarunek/pdnsd` states that `master` points to latest release `1.2.9a-par`.
- Pinned source archive: `https://github.com/kwarunek/pdnsd/archive/c77e16f2c0c5bd146de181c0a507c38a437b6f7d.tar.gz`
- SHA-256: `44533225e19a2ba94e65dce989482542d7e6a5ebf710de430219bfc47ffa31ed`

## Build

- Build system: pre-generated Autotools configure script.
- Configure target: Linux-compatible code path for Linux/OHOS packaging.
- Thread library: NPTL, selected explicitly to avoid configure-time thread probing ambiguity.
- Default id: root, selected to avoid package-install chown operations against `nobody` in CI packaging directories.
- Source compatibility: `src/icmp.c` includes `net/if.h` before `linux/icmp.h` on Linux so current glibc headers do not redeclare `IFF_*` values and `struct ifreq`.
- OHOS cross builds use direct DevEco clang compilation with a configure-equivalent `config.h`, because this Windows precheck host has no Unix shell/make environment for Autotools `configure`.

## Upstream tests

The upstream release provides four diagnostic programs in `src/test/Makefile.am`:

- `if_up`
- `is_local_addr`
- `tping`
- `random`

`make check` builds these four programs. When target binaries can run, the recipe executes all four with deterministic local inputs:

- `if_up lo`
- `is_local_addr 127.0.0.1`
- `tping 127.0.0.1`
- `random`

## Consumer tests

`test_package` exercises the installed `pdnsd` and `pdnsd-ctl` commands with
version/help checks, verifies the upstream-defined `pdnsd` informational
command exit status, and runs one invalid-option fault-injection case.

On OHOS CI, the runtime shell is provided at `/data/service/hnp/bin/bash` while
`/bin/bash` is not present. The test package therefore resolves `bash` from
`CONFIG_SHELL`, `PATH`, the OHOS tool path, and finally `/bin/bash` so the same
script runs on both OHOS workers and normal Linux hosts.
