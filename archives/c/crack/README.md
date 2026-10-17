# crack

Crack v5.0a — the classic Unix password cracker by Alec Muffett
(1991-1996). Local password-security checking tool: it attacks DES
crypt(3) password hashes with a dictionary + rule-mangling engine and a
DAWG-compressed wordlist format.

- Homepage: https://packages.debian.org/sid/crack
- License: Crack v5.0 LICENCE (freely distributable)
- Build system: hand-rolled Makefile (no configure; the `Crack` driver
  script wraps `src/lib` + `src/util` builds)
