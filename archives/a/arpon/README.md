# ArpON (ARP handler inspection)

ArpON (ArpON - ARP handler inspection) is a host-based ARP handler
inspection tool that provides SARPI, DARPI and HARPI anti-ARP-spoofing
techniques.

## Description

ArpON is a portable ARP handler inspection/sniffer-based daemon tool
forlocalhost network analysis and ARP inspection. It detects and
blocks ARP poisoning and spoofing attacks.

### Techniques

- **SARPI** (Static ARP Inspection): blocks ARP poisoning attacks in
  static networks
- **DARPI** (Dynamic ARP Inspection): blocks ARP poisoning attacks in
  dynamic networks
- **HARPI** (Hybrid ARP Inspection): blocks ARP poisoning attacks in
  hybrid networks

## Version

- 3.0-ng

## Dependencies

- libnet/1.2
- libpcap/1.10.6
- libdnet/1.12

## Build System

CMake

## License

BSD-2-Clause
