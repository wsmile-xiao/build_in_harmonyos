# tcping

TCP Ping utility - check if a TCP port is reachable.

## Description

tcping is a command-line utility that tests TCP port connectivity. Unlike traditional ping which uses ICMP, tcping establishes TCP connections to determine if a port is open, closed, or timing out.

## Usage

```bash
tcping [-q] [-f <4|6>] [-t timeout_sec] [-u timeout_usec] <host> <port>
```

### Options

- `-q`: Quiet mode (suppress output)
- `-f <4|6>`: Force IPv4 or IPv6
- `-t timeout_sec`: Timeout in seconds
- `-u timeout_usec`: Timeout in microseconds

### Examples

```bash
# Test if port 80 is open on localhost
tcping localhost 80

# Test SSH port with timeout
tcping -t 5 example.com 22

# Quiet mode test
tcping -q example.com 443
```

## Dependencies

- No external dependencies (uses standard C library)

## OpenHarmony Adaptation

- Uses clang compiler
- Modified Makefile to support DESTDIR installation
- Added install target for packaging

## Build System

- Type: Makefile (simple, no autotools)
- Compiler: clang

## License

Copyright (c) 2002-2023 Marc Kirchner

