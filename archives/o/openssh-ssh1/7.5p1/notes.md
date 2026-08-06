# openssh-ssh1 7.5p1

## Adaptation notes

- Uses the official OpenSSH portable 7.5p1 source archive.
- W0 dependencies are available in the `ohpcd` remote:
  - `zlib/1.3.1.1`
  - `openssl/1.1.1w`
- Applies small Autotools portability patches for OHOS:
  - accept `linux-ohos` host triplets in `config.sub`;
  - avoid `umask 077` temporary directories that fail on OHOS HMDFS.
- Disables platform integrations not available in the OpenHarmony environment:
  sandbox, utmp/utmpx, wtmp/wtmpx, and lastlog.
- OpenSSL 1.1.0 introduced opaque RSA and DSA structures; OpenSSL 1.1.1w has
  the same API requirement. The upstream 7.5p1 SSH1 code directly dereferences
  RSA, DSA, and DH members, so the recipe backports accessor-based replacements
  (`RSA_get0_*`, `RSA_set0_*`, `DSA_get0_*`, `DSA_set0_*`, and `DH_get0_*`) in
  `0003-openssl-1.1-accessors.patch`.
- OpenSSL 3.x is not the point at which these structures became opaque; the
  existing `openssl/1.1.1w` package is retained and no separate OpenSSL change
  is required.

## Tests

- Upstream: `make tests`, covering the 14 default OpenSSH regression targets
  declared by `REGRESS_TARGETS` in `regress/Makefile`.
- Consumer: `test_package` checks the 7.5p1 version, runs `ssh -1 -G`, and
  creates an SSH1 RSA key pair with `ssh-keygen -t rsa1`. On OHOS, SELinux
  exposes no writable+executable partition to the CI account (writable areas
  carry labels that forbid execution; the executable area is read-only), so
  the recipe's `test()` falls back to compile-time assertions over the
  packaged artifacts (file exists, ELF magic, executable bit). The runtime
  smoke still runs on Linux and on OHOS devices that expose a
  writable+executable partition.
