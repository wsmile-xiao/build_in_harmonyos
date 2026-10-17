#!/usr/bin/env python3
"""netaddr consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually call the tested API — IPAddress parse/format and
CIDR containment (pure user-space).

Usage: test_netaddr.py <site-packages>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "netaddr")):
        raise AssertionError(f"netaddr package missing in {site}")
    sys.path.insert(0, site)
    # R34: 真实调用被测库 API
    import netaddr

    ip = netaddr.IPAddress("192.168.1.1")
    if str(ip) != "192.168.1.1" or int(ip) != 0xC0A80101:
        raise AssertionError(f"unexpected IPAddress result: {ip}")
    net = netaddr.IPNetwork("192.168.1.0/24")
    if not (netaddr.IPAddress("192.168.1.55") in net):
        raise AssertionError("IPNetwork containment failed")
    print(f"OK: netaddr {netaddr.__version__} "
          f"(IPAddress parse {ip} + CIDR containment ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
