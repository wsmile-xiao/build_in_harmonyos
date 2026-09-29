# pgpgpg for OpenHarmony

`pgpgpg` is a command line front end that accepts PGP 2.6 style options,
translates them into GnuPG options and then executes `gpg`.

## Package details

- Upstream: https://mroth.net/pgpgpg/
- Build system: GNU Autotools (the release tarball already ships `configure`)
- Target: OpenHarmony/HarmonyOS aarch64
- Executed external program: GnuPG (`gnupg/2.4.9.1`), not a link-time library

## Runtime notes

`pgpgpg` never dlopen()s or links a crypto library: it `execv()`s the gpg
binary whose absolute path was probed at configure time. The path is compiled
into the program (`GPG_PATH`), so it does not follow `PATH` at run time. The
Conan recipe passes `--with-gpg-path=<gnupg package_folder>/bin/gpg`, which
ties the produced binary to the Conan cache layout used at build time.

## Versions

| Version | Status |
| --- | --- |
| 0.13 | built |
