# socklog

socklog is a system and kernel logging service: in cooperation with the
[runit](https://smarden.org/runit/) package it provides a small and secure
replacement for `syslogd`. It receives log messages from an UNIX datagram
socket (`/dev/log`), from the kernel log device, or from the network, and
passes each message to a user-supplied handler program without holding the
messages itself.

## HarmonyOS PC adaptation

- Version: 2.1.2
- Build system: makefile (smarden `conf-cc`/`conf-ld` style, no configure script)
- Recipe: `2.1.2/conanfile.py`
- Upstream: <https://smarden.org/socklog/>

## Provided commands

| Command | Purpose |
|---|---|
| `socklog` | receives log messages and dispatches them to a handler |
| `socklog-check` | checks whether a `socklog` instance is up and receiving |
| `socklog-conf` | creates the service and log directories for `socklog` |
| `tryto` | runs a program until it succeeds, or gives up |
| `uncat` | reads its input once and feeds it to a program repeatedly |
