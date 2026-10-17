# gsan

gsan scans TLS certificates and reports DNS names and IP addresses found in the subject alternative name extension.

## OpenHarmony adaptation

Version 5.0.0 is adapted for OpenHarmony PC as a self-contained Python application. The adaptation replaces unavailable runtime dependencies (`typer`, `rich`, `pyasn1`, `cryptography`, and `pyOpenSSL`) with Python standard-library implementations and an `argparse` command line interface.

## Usage

```text
gsan example.com
gsan example.com --format json
gsan example.com:8443 --timeout 5
```

The package requires Python 3.10 or newer.
