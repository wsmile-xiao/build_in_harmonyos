#!/usr/bin/env python3
"""Conan test_package for ausweisapp-nftrules — R34 real content verification.

ausweisapp-nftrules is a pure data package: a single nftables ruleset file.
The verifiable artifact is <pkg>/etc/nftables.d/ausweisapp.nft. This test
asserts the file exists and its content carries the expected nft rule
(accept connections for BundID AusweisApp2 on tcp dport 24727) — real
content verification, not just file presence.
"""
import os
import sys


def main():
    pkg = sys.argv[1]
    rule = os.path.join(pkg, "etc", "nftables.d", "ausweisapp.nft")
    if not os.path.isfile(rule):
        print(f"FAIL: {rule} not found", file=sys.stderr)
        return 1
    with open(rule, "r", encoding="utf-8") as f:
        content = f.read()
    # R34: assert the ruleset actually carries the expected nft rule.
    if "table inet filter" not in content:
        print("FAIL: ruleset missing 'table inet filter'", file=sys.stderr)
        return 1
    if "dport 24727" not in content or "accept" not in content:
        print("FAIL: ruleset missing 'tcp dport 24727 accept' rule",
              file=sys.stderr)
        return 1
    print("OK: ausweisapp-nftrules ruleset verified (24727 accept)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
