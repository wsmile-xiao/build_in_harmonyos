# udpxy

udpxy is a small-footprint UNIX/Linux daemon that relays multicast UDP traffic
to HTTP clients. The `1.0.25.1` recipe builds the upstream raw-Makefile project
(`chipmunk/` subdir, GitHub tag `1.0-25.1`) into the `udpxy` and `udpxrec`
command line tools. It has zero third-party dependencies; the only source patch
adds the `-h/--help` exit-0 CLI contract (error paths keep the upstream
`ERR_PARAM` contract). Upstream's six standalone unit-test programs in
`chipmunk/test/` (no make target) are compiled and executed inside the recipe
`build()`; the `test_package` asserts the CLI contract plus a live HTTP status
page served on loopback.
