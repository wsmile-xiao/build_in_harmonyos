# tuptime

`tuptime` reports historical and statistical system uptime, preserved across
reboots — "like `uptime`, but with extended information".  Every system
startup/shutdown is registered in a SQLite database and summarised as system
life, longest/average uptime and downtime, percentage availability, boot id and
kernel string.

- Upstream: <https://github.com/rfmoz/tuptime> (release `5.2.5`,
  tag `5.2.5`, tarball `tuptime-5.2.5.tar.gz`,
  sha256 `a4dfeac8221688be1452273458d69075c83a2ecad0dc8a27f973e8456737ec48`)
- License: GPL-2.0-or-later

## What this package provides

| Path | Content |
|---|---|
| `bin/tuptime` | the whole program (single-file Python 3 script, upstream `src/tuptime`) |
| `share/man/man1/tuptime.1` | upstream man page |
| `share/doc/tuptime/tuptime-manual.txt` | upstream reference manual (database schema, integration notes) |
| `licenses/LICENSE` | upstream license |

It is an **interpreted script tool**: there is no C/C++ source and therefore no
`build()` step — the recipe fetches the release tarball, applies the OHOS
portability patch and installs the script (`package_type = "application"`).

Runtime requirement: a Python 3 interpreter (standard library only — `sqlite3`,
`argparse`, `locale`, `platform`, `signal`, `logging`, `time`, `datetime`).
There are no third-party Conan dependencies.

## HarmonyOS (OHOS) port

`patches/0001-src-tuptime.patch` — one-line backend selection change (+4/-1):

CPython on OpenHarmony reports `sys.platform == 'ohos'`.  Upstream picks a
backend with `sys.platform.startswith('linux')` / a BSD tuple, and **any other
value aborts**:

```
ERROR:root:System = ohos not supported
$ echo $?
1
```

i.e. the tool is completely unusable on OHOS.  OHOS runs the HongMeng kernel
but still exposes the Linux `/proc` interface (`/proc/uptime`, `/proc/stat`,
`/proc/sys/kernel/random/boot_id`) and the `clock_gettime()` clocks
(`CLOCK_BOOTTIME`/`CLOCK_MONOTONIC`) that `os_linux()` consumes, so the patch
routes `ohos` into the Linux backend:

```python
-    if sys.platform.startswith('linux'):
+    if sys.platform.startswith(('linux', 'ohos')):
         sis = os_linux(sis)
```

The patch contains no platform macro and no stub.

### Default database path

The upstream default is `/var/lib/tuptime/tuptime.db`, a path the distribution
packager is expected to provision (`tuptime-install.sh` creates the
`_tuptime` user and the directory).  On a HarmonyOS PC `/var` is a read-only
mount, so without that provisioning the default path is unavailable; use `-f`
or the upstream `TUPTIME_DBF` environment variable (honoured, by upstream
design, only while the default path is in effect) to point at a writable file:

```console
$ tuptime -f "$HOME/.local/share/tuptime/tuptime.db"
$ TUPTIME_DBF="$HOME/.local/share/tuptime/tuptime.db" tuptime
```

This is a system-provisioning matter rather than an OHOS-specific code defect,
so the default constant is deliberately left untouched.

## Usage

```console
$ tuptime                    # summary report
$ tuptime -t                 # table of every register
$ tuptime -l                 # list of every register
$ tuptime -c                 # CSV output
$ tuptime -s                 # timestamps in epoch seconds
$ tuptime -k                 # include the kernel string
$ tuptime -g                 # register a graceful shutdown
```

See `share/man/man1/tuptime.1` and `share/doc/tuptime/tuptime-manual.txt`.

## Tests

* Upstream: two Debian autopkgtests (`debian/tests/exec-simple`,
  `debian/tests/exec-debug`) plus the SQLite checker
  `misc/scripts/tuptime_dbcheck.py` (10 cases).  All were executed for real on
  HarmonyOS — see `5.2.5/reports/`.
* Package: `test_package/test_tuptime.py` — 11 executable assertions against
  the installed `bin/tuptime`, including the HarmonyOS-only
  `ohos-platform-backend` case.  Ledger: `5.2.5/test_package/MANIFEST.yml`.
