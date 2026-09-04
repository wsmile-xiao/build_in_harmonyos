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

Adapted to HarmonyOS PC (aarch64, musl, clang 15) as the third cwrap
family member in this repository, after pam-wrapper/1.1.8 and
nss-wrapper/1.1.16.

Homepage: https://gitlab.com/cwrap/socket_wrapper
