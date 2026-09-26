# mini-httpd

mini_httpd - a tiny HTTP server by ACME Labs (Jef Poskanzer), with the
`htpasswd` credential utility.

- Upstream: https://www.acme.com/software/mini_httpd/
- Adapted version: 1.30 (branch feat/mini-httpd-1.30, task 13916, activity 6)
- Build system: bare Makefile (CC/CFLAGS/LDFLAGS overridden per R33); no
  external dependencies (SSL support is opt-in and left off; crypt via libcrypt)
- Upstream tests: none shipped (N_static=0); consumer smoke test covers
  htpasswd credential creation and a live loopback HTTP round-trip
- Special handling: musl getpass() portability patch (termios-based),
  E077 package-time signing, upstream -s strip dropped to preserve .codesign
