# doh

A stand-alone DNS-over-HTTPS resolver using libcurl.

This is a simple C application from the curl project that resolves a host
name using DNS-over-HTTPS (DoH). It uses POST requests unconditionally.

## Usage

    doh [options] host [DoH URL]

If DoH URL is left out, the Cloudflare DoH server will be used.

Options:
- `-h` shows help output
- `-t` enables server test mode
- `-v` enables verbose mode
- `-k` enables insecure mode, skipping server certificate validation
- `-V` shows version

## License
MIT

## Source
https://github.com/curl/doh
