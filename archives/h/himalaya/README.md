# himalaya

CLI email client written in Rust. Supports IMAP, SMTP, Maildir, and PGP.

## Homebrew Stats

- Install count: 83,549

## Key Features

- IMAP, SMTP, Sendmail backend support
- Maildir local storage
- PGP support (commands, native, GPG)
- Account configuration wizard
- Envelope listing, searching, and sorting

## Build Notes

- Rust/Cargo project — requires Rust toolchain for source compilation
- Pre-compiled binary deployment (musl) on HarmonyOS
- glibc static binaries crash on HarmonyOS (musl libc)
- rustc itself crashes on HarmonyOS, cannot compile from source

## Version History

- 1.1.0-r0: built (using Alpine 1.2.0-r0 musl binary as substitute)
