# udptunnel

udptunnel tunnels UDP packets over a TCP connection, crossing networks that
only pass TCP traffic. The `1.1` recipe builds the upstream autotools project
(2001-era autoconf 2.13 configure, which never invokes config.guess) into the
`udptunnel` command line tool. It has zero third-party dependencies; the only
source patches drop the dead NIS/YP fallback in host2ip() (rpcsvc/ypclnt.h is
absent on OHOS/musl) and add the `-h/--help` exit-0 CLI contract.
