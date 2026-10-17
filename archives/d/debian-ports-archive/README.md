# debian-ports-archive

https://salsa.debian.org/aurel32/debian-ports-archive-keyring

The debian-ports archive digitally signs its Release files with the OpenPGP
archive certificates contained in this package (upstream source package name:
`debian-ports-archive-keyring`). The keys let package managers authenticate
the archive they fetch from.

## OHOS Adaptation

- Pure data package: the ASCII-armored key files are installed under
  `share/keyrings/debian-ports-archive/`, nothing to compile.
- Upstream builds assembled keyrings into `/etc/apt/trusted.gpg.d` (conffiles)
  using gnupg; on OHOS we ship the individual key files and expose the key
  directory through the `DEBIAN_PORTS_ARCHIVE_KEYS` runenv variable.
- The consumer-side test verifies every shipped key is a well-formed armored
  public key block and that the active/removed inventory is complete.

## Usage

Import the key files into your verification tooling:

```
share/keyrings/debian-ports-archive/active-keys/*.key
```

## Installation layout

- `share/keyrings/debian-ports-archive/active-keys/*.key` — currently active keys
- `share/keyrings/debian-ports-archive/removed-keys/*.key` — retired keys