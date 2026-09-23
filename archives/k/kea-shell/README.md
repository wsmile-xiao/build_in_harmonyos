# Kea Shell

`kea-shell` is the text client ISC Kea ships for the REST interface of its
servers (`kea-dhcp4`, `kea-dhcp6`, `kea-dhcp-ddns` and the Control Agent).  It
sends control commands over HTTP/HTTPS and prints the JSON response, which makes
it a convenient way to drive `config-get` / `config-set` / `list-commands` from
a shell script.

## Package contents

- Command-line tool: `bin/kea-shell`
- Helper modules imported by the tool: `bin/kea_conn.py`,
  `bin/kea_connector3.py`
- License: MPL-2.0

## OpenHarmony adaptation

`kea-shell` is a Python 3 script tool: the upstream Meson target in
`src/bin/shell` declares no compilation and no `dependencies:`/`link_with:` at
all.  Its only build action is `configure_file()` -- expanding `kea-shell.in`
into the `kea-shell` script and copying the two helper modules -- so this
package stops after the upstream configure phase and ships the generated files
without compiling anything.

The Kea Meson project is configured as a whole, so the project-level configure
gate (boost, openssl, log4cplus) is declared as a build-time dependency; those
libraries are consumed by the configure probes only and are not linked into the
shipped artefact.

Two portability patches are applied:

- the Meson system name is normalized from `harmonyos` to `linux`, otherwise
  Kea's platform branch aborts the configure;
- the generated script uses `/usr/bin/env python3` instead of the absolute path
  of the build machine's interpreter, which upstream writes into the shebang.

## Usage

```sh
# list the commands a DHCPv4 server exposes
kea-shell --host 192.0.2.1 --port 8000 --service dhcp4 list-commands

# send a configuration command with arguments on stdin
echo '{ "loggers": [] }' | kea-shell --host 192.0.2.1 config-set

# HTTPS with a private CA and a client certificate
kea-shell --host 192.0.2.1 --port 8001 --ca ./kea-ca.crt \
          --cert ./client.crt --key ./client.key list-commands
```

Upstream: https://www.isc.org/kea/ -- https://gitlab.isc.org/isc-projects/kea
