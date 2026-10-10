# Kea Admin

`kea-admin` is the database administration tool ISC Kea ships for its lease
databases.  It initializes a new database, reports and upgrades the schema
version, dumps leases to memfile-ready CSV and uploads them back, and recounts
lease statistics.  It drives the `mysql` and `pgsql` back-ends through their
command-line clients (`memfile` operations are upstream stubs that report
`NOT IMPLEMENTED`).

## Package contents

- Command-line tool: `bin/kea-admin`
- Shared helper sourced by the tool and by every maintenance script:
  `share/kea/scripts/admin-utils.sh`
- MySQL maintenance scripts: `share/kea/scripts/mysql/` --
  `dhcpdb_create.mysql`, `dhcpdb_drop.mysql`, `wipe_data.sh` and the 40
  `upgrade_*.sh` schema upgrade scripts
- PostgreSQL maintenance scripts: `share/kea/scripts/pgsql/` --
  `dhcpdb_create.pgsql`, `dhcpdb_drop.pgsql`, `wipe_data.sh` and the 34
  `upgrade_*.sh` schema upgrade scripts
- License: MPL-2.0

## OpenHarmony adaptation

`kea-admin` is a POSIX shell script tool: the upstream Meson target in
`src/bin/admin` declares no compilation and no `dependencies:`/`link_with:` at
all.  Its only build actions are `configure_file()` -- expanding `kea-admin.in`
into the `kea-admin` script and `admin-utils.sh.in` into the shared helper, and
materialising the database maintenance scripts -- so this package stops after
the upstream configure phase and ships the generated files without compiling
anything.

The Kea Meson project is configured as a whole, so the project-level configure
gate (boost, openssl, log4cplus) is declared as a build-time dependency; those
libraries are consumed by the configure probes only and are not linked into the
shipped artefacts.

The platform adaptation covers three areas:

- the Meson system name is normalized from `harmonyos` to `linux`, otherwise
  Kea's platform branch aborts the configure;
- upstream resolves `admin-utils.sh` and the maintenance scripts through the
  absolute configure-time prefix, which inside a Conan package would be the
  non-existent `/share/kea`: the script now locates its runtime pieces relative
  to its own location (`<package>/bin/kea-admin` ->
  `<package>/share/kea/scripts`), and the upgrade/wipe scripts do the same for
  the helper they source;
- the HarmonyOS PC kernel refuses `execve()` of `#!/bin/sh` scripts regardless
  of the executable bits, so kea-admin itself, the upgrade scripts it forks and
  the upstream shell test suites are all started through `sh` (the Meson
  configure steps are replicated in the recipe for the same reason).

## Usage

```sh
# initialize a mysql lease database
sh <package>/bin/kea-admin db-init mysql -u '<db-user>' -p '<db-password>' -h 127.0.0.1 -n keatest

# check and upgrade the schema
sh <package>/bin/kea-admin db-version mysql -u '<db-user>' -p '<db-password>' -h 127.0.0.1 -n keatest
sh <package>/bin/kea-admin db-upgrade mysql -u '<db-user>' -p '<db-password>' -h 127.0.0.1 -n keatest

# the same for PostgreSQL
sh <package>/bin/kea-admin db-init pgsql -u '<db-user>' -p '<db-password>' -h 127.0.0.1 -n keatest
```

`lease-dump` and `lease-upload` additionally need the `kea-lfc` binary to
preprocess the CSV files; `kea-lfc` and the Kea servers are separate targets of
the upstream project and not part of this package.

Upstream: https://www.isc.org/kea/ -- https://gitlab.isc.org/isc-projects/kea
