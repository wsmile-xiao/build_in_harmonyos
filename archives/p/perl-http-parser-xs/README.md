# perl-http-parser-xs

HTTP::Parser::XS - A fast, primitive HTTP request/parser

## Description

HTTP::Parser::XS is a Perl XS module that provides fast HTTP request and response parsing using the picohttpparser C library.

## Features

- Fast HTTP request parsing (XS implementation)
- HTTP response parsing with multiple header format options
- Pure Perl fallback (HTTP::Parser::XS::PP) for compatibility

## Versions

| Version | Status | Date |
|---------|--------|------|
| 0.17-r9 | built | 2026-06-11 |

## Dependencies

- perl >= 5.42.0

## OpenHarmony Notes

This Perl XS module requires special linking parameters on OpenHarmony:
- `-nostartfiles -nodefaultlibs -lc` to bypass missing CRT files

## Usage

```perl
use HTTP::Parser::XS;

# Parse HTTP request
my $env = {};
my $ret = HTTP::Parser::XS::parse_http_request($request, $env);

# Parse HTTP response
my ($ret, $minor, $status, $msg, $headers) =
    HTTP::Parser::XS::parse_http_response($response, HEADERS_AS_HASHREF);
```

## Installation

```bash
# Install from precompiled package
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-http-parser-xs 0.17-r9
```

## References

- CPAN: https://metacpan.org/pod/HTTP::Parser::XS
- GitHub: https://github.com/kazuho/p5-http-parser-xs