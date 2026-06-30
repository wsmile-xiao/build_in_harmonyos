---
# ipcalc

A modern IPv4/IPv6 ipcalc tool, assisting in network calculations.

ipcalc takes an IP address and netmask and calculates the resulting broadcast,
network, Cisco wildcard mask, and host range. It can also be used to determine
if an IP address belongs to a given network/subnet.

This is the modern C implementation (not the Python/Perl versions).

## Features

- IPv4 and IPv6 address calculation
- Network, broadcast, and host range computation
- Address containment checking
- GeoIP and MaxMindDB support (optional, disabled in this build)

## Versions

| Version | Status | Date |
|---------|--------|------|
| 1.0.3 | published | 2026-05-25 |