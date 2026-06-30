# irssi

irssi is a modular IRC (Internet Relay Chat) client for UNIX systems. It supports multiple IRC networks, DCC file transfers, and various scripting interfaces.

## Key Features
- Text-based IRC client with terminal UI
- SSL/TLS support via OpenSSL
- Multiple network connections
- DCC chat and file transfer support
- Modular architecture with plugin support

## Compiled Version
- **Version**: 1.4.5
- **Platform**: HarmonyOS (aarch64-unknown-linux-ohos)
- **Build System**: Autotools
- **Dependencies**: glib 2.88.0, OpenSSL 3.5.6, ncurses 6.5-20250215

## Notes
- Perl scripting support is disabled (--with-perl=no) due to platform limitations
- Config.guess/config.sub patched for HarmonyOS recognition (E007)
