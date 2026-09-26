# diaspora-installer

https://wiki.debian.org/Diaspora

diaspora-installer is the Debian packaging of the set-up helper for running a
diaspora* pod. Diaspora* is a free, distributed social networking service
(AGPL/Ruby on Rails). This package ships the POSIX shell scripts and
configuration templates that download the diaspora* code, initialize its
PostgreSQL/MySQL database and hook it up to nginx.

The upstream source is Debian packaging (`ruby-team/diaspora-installer`); the
conan package distributes the installer scripts and config templates.

## OHOS Adaptation

- Pure data bundle — there is no binary to build.
- `diaspora-versions.sh` is a side-effect free helper that exports the
  diaspora version variables; it is exposed on PATH.
- Scripts that require Debian runtime hosts (`grantpriv.sh`, `adduser.sh`,
  `initdb.sh`, ...) reference `psql`/`adduser`/`/etc/diaspora` and are shipped
  as reference material only — the test never executes them.
- The `DIASPORA_INSTALLER_DIR` runenv points consumers at the config/script
  directory.

## Usage

Source the version helper to inspect embedded versions:

```
. share/diaspora-installer/diaspora-versions.sh   # exports diaspora_version=0.9.0.0
```

## Installation layout

- `share/diaspora-installer/*.sh` — installer scripts
- `share/diaspora-installer/*.conf|*.toml|*.example|database.yml` — config templates
- `licenses/debian/copyright` — GPL-2+