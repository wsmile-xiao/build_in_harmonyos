# mdns-scan

A tool for scanning for mDNS/DNS-SD published services on the local network.

## Description

mdns-scan is a command-line tool by Lennart Poettering that issues a mDNS PTR
query to the special RR `_services._dns-sd._udp.local` for retrieving a list
of all currently registered services on the local link.

It is intended for usage as a debugging tool only. It does not terminate on
its own — it scans for services continuously until killed with Ctrl-C.

## Homepage

https://0pointer.de/lennart/projects/mdns-scan/

## License

GPL-2.0-or-later

## Versions

| Version | Status |
|---------|--------|
| 0.5     | built  |
