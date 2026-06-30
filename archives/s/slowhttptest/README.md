# slowhttptest

Application Layer DoS attack simulator - a tool to test for slow HTTP DoS vulnerabilities.

## Description

slowhttptest is a highly configurable tool that simulates some Application Layer Denial of Service attacks by prolonging HTTP connections in an asymmetrical way. It works in the following modes:

- **Slowloris**: Sends incomplete HTTP requests, keeping connections open
- **Slow HTTP POST**: Sends POST requests with slow body transmission
- **Slow Read**: Reads HTTP responses slowly, keeping server resources occupied
- **Range Header**: Exploits HTTP range headers to cause resource exhaustion

## Testing Use Cases

- Verify HTTP server's resilience against slow DoS attacks
- Test timeout configurations
- Evaluate connection handling capacity
- Security auditing and penetration testing

## Version

- **1.9.0** (latest stable)

## Dependencies

- OpenSSL 1.1.1w (included in precompiled package)

## Build System

- autotools

## Usage Example

```bash
# Test against a web server
slowhttptest -H -c 1000 -i 10 -r 200 -t GET -u https://target.example.com -x 24

# Show help
slowhttptest -h
```

## Notes

- HMDFS filesystem requires special handling for configure temporary directories
- Precompiled package includes OpenSSL runtime libraries in `lib/external/`
- Tool should only be used for authorized security testing