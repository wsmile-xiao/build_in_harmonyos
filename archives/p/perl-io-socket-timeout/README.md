# perl-io-socket-timeout

IO::Socket::Timeout - Perl module for socket timeout handling

## Description

IO::Socket::Timeout is a Perl module that provides timeout handling for IO::Socket connections. It allows setting read and write timeouts on socket connections.

## Features

- Read and write timeout support for sockets
- Works with IO::Socket::INET and IO::Socket::SSL
- Pure Perl implementation (no XS code)
- Compatible with Perl 5.42.0

## Dependencies

### Runtime Dependencies
- PerlIO::via::Timeout 0.32

### Build Dependencies
- Perl 5.42.0

## Installation

This module is typically installed via the cmd-pkgs installation script:

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-io-socket-timeout 0.32-r2
```

## Usage

```perl
use IO::Socket::Timeout;

# Create socket with timeout
my $socket = IO::Socket::INET->new(
    PeerAddr => 'example.com',
    PeerPort => 80,
    Timeout  => 30
);

# Set read/write timeouts
IO::Socket::Timeout->apply_timeout($socket, read => 10, write => 20);
```

## Notes

- This is a pure Perl module (no compiled binaries)
- No ELF signature required
- Must install PerlIO::via::Timeout dependency first

## Version History

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 0.32-r2 | built | 2026-06-12 | Precompiled package ready (21KB), quality gates PASS |

## Test Results (2026-06-12)

| Test | Status | Notes |
|------|--------|-------|
| File Integrity | PASS | All .pm files present |
| Version Check | PASS | VERSION = 0.32 |
| Syntax Parse | PASS | Perl -c OK |
| Module Load | PASS | IO::Socket::Timeout loads correctly |
| XS Dependency | PARTIAL | IO.so SELinux limitation (E046, known platform issue) |

See `reports/test-report.md` for detailed test report.

## Packaging

**Precompiled Package**: `perl-io-socket-timeout-0.32-r2-ohos-aarch64.tar.gz` (21KB)

**Contents**:
- `lib/site_perl/5.42.0/IO/Socket/Timeout.pm`
- `lib/site_perl/5.42.0/aarch64-linux/auto/IO/Socket/Timeout/.packlist`

**Quality Gates**: All PASS (G1-G4)

## License

Perl Artistic License or GPL v1+