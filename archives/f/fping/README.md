---
# fping

A utility to ping multiple hosts at once.

fping is a fast, parallel ping utility that can ping many hosts simultaneously.
Unlike traditional ping which sends ICMP requests one at a time, fping sends
requests to all targets in parallel, making it ideal for network monitoring
and scanning.

## Features

- Parallel ICMP ping to multiple targets
- Supports reading targets from file or stdin
- Round-robin and random ping modes
- Per-target timing statistics
- IPv4 and IPv6 support

## Versions

| Version | Status | Date |
|---------|--------|------|
| 5.3 | published | 2026-05-25 |