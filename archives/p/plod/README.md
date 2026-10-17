# PLOD for HarmonyOS

PLOD (Personal LOgging Device) is a small Perl command-line utility for keeping timestamped administrator notes.

## Features

- Add a one-line or interactive log entry.
- Read, search, page or edit current and historical log files.
- Customize paths and behavior through environment variables or `.plodrc`.

## HarmonyOS adaptation

PLOD is a single Perl script, so no C/C++ compilation is needed. The package depends on `perl/5.42.2`, installs the command as `bin/plod`, changes its obsolete `/usr/local/bin/perl` shebang to the HarmonyOS HNP Perl path, and disables the unavailable legacy `/usr/bin/crypt` default. Logs are plaintext by default. Encryption can still be enabled explicitly through PLOD's existing `CRYPTCMD` override.

Test the packaged script directly on the HarmonyOS computer using Conan test_package. Host-side packaging alone does not establish that runtime tests passed.

## Dependencies

- Runtime: `perl/5.42.2`

## References

- Archived upstream site: <https://web.archive.org/web/20160821040241/https://deer-run.com/~hal/plod/>
- Verified release mirrors: <https://gentoo.osuosl.org/distfiles/eb/plod-1.9.tar.gz>, <https://mirror.ibcp.fr/pub/gentoo/distfiles/eb/plod-1.9.tar.gz>
