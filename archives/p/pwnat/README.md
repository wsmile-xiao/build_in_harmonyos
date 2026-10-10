# pwnat

pwnat is an upstream UDP NAT traversal command-line tool. The 0.3.0 recipe
overrides the upstream Makefile's hard-coded `gcc` using the Conan-configured C
compiler. Its consumer smoke test checks help output without attempting a
privileged network tunnel.

The 0.3.0 recipe passed a HarmonyOS PC `conan create` and one packaged-command
consumer check on 2026-10-06. The help check does not establish that raw ICMP
sockets or end-to-end NAT traversal work; platform PR CI remains pending.
