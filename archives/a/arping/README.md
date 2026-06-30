# arping

ARP ping utility for network discovery and address resolution.

arping is a utility that sends ARP requests to a specified host and
displays the replies. It can be used to discover hosts on a local
network, detect IP address conflicts, and verify MAC address bindings.
Unlike ICMP ping, arping operates at the ARP layer, making it useful
when ICMP is blocked or filtered.

## Features

- ARP-level host discovery (works even when ICMP is blocked)
- Detect IP address conflicts (duplicate IP detection)
- Verify MAC address bindings
- Supports both ARP and ICMP ping modes
- Gratuitous ARP support

## Versions

| Version | Status | Date |
|---------|--------|------|
| 2.26 | built | 2026-05-26 |