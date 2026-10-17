# socket-wrapper

A library passing all BSD sockets API calls through a Unix socket.
Part of the [cwrap](https://cwrap.org/) project family: `socket_wrapper`
is an `LD_PRELOAD` interposition library that redirects TCP/UDP socket
traffic (socket/bind/connect/accept/...) to local Unix domain sockets so
that full network integration tests can run unprivileged and in
isolation.

The `libsocket_wrapper_noop.so` stub is the link-time companion for
socket_wrapper-aware applications that call the public helpers
(`socket_wrapper_enabled()`, `socket_wrapper_indicate_no_inet_fd()`,
`socket_wrapper_syscall_valid()`, `socket_wrapper_syscall_va()`).

Adapted to HarmonyOS PC (aarch64 and x86_64, musl, clang 15). The port
handles the musl `recvmmsg`/`sendmmsg` prototypes and LFS64 macro aliases.
Packaged shared objects and target test executables are re-signed with the
HarmonyOS SDK tools after stale `.codesign` sections are removed.

Upstream tests honor `TMPDIR`. The 1.4.1 test deployment can also use
`SOCKET_WRAPPER_ECHO_SERVER` to select the deployed echo server. At runtime,
`SOCKET_WRAPPER_DIR` must be a short, writable path on a native filesystem
that permits AF_UNIX socket creation.

Homepage: https://gitlab.com/cwrap/socket_wrapper
Official release archives: https://ftp.samba.org/pub/cwrap/
