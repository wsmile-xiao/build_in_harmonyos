# util-linux-login — PAM-based login(1) from util-linux

`login` is the standard Unix login program from the [util-linux](https://github.com/util-linux/util-linux) suite. It authenticates users via PAM (Pluggable Authentication Modules), sets up the user session, and updates utmp/wtmp records.

`nologin` is a restricted shell replacement that politely refuses logins.

This Conan package builds **only** `login` and `nologin` from the full util-linux source tree, using `--disable-all-programs` to disable all other utilities.

## Dependencies

- **linux-pam**: PAM authentication framework (libpam, libpam_misc)

## Build System

Autotools (`configure.ac` + `Makefile.am`)

## Platform Notes

- Requires PAM configuration (`/etc/pam.d/login`) at runtime
- `login` typically needs SUID root permissions
- `config.sub` v2.42.2 already supports `linux-ohos*` natively
