# OHOS distributed fs denies file-create inside mktemp 0700 dirs and O_APPEND opens for the conan task

> **Contributor**: codex | **Status**: DRAFT | **Created**: 2026-09-13

## Symptom

An autotools `configure` run inside a conan-home on `/storage/Users` fails at
the very last step with:

```
config.status[1510]: can't create .../tmp/confXXXXXX/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

while the very same create/append operations succeed when typed in an
interactive SSH shell in the same directory. Other runs also show
`./libtool: bad interpreter: Permission denied` for freshly built libtool
scripts, or intermittent `ENOENT` on paths that exist.

## Root cause

`/storage/Users` is a distributed fs (presented as tmpfs, `hmmac=use_task`).
Two independent behaviors were measured on an affected device:

1. `mktemp -d` creates the directory with mode 0700 and the ACL is fixed at
   creation time. Inside such a directory even the owning task cannot create
   files. `chmod 777` after creation does not repair it — the ACL was baked
   when the directory was created with the restrictive mode.
2. Opens with `O_APPEND` (`cat >> file`, `echo >> file`) issued from the
   conan process tree are denied with EACCES, while the same operations from
   an interactive SSH session succeed.

Autoconf 2.71's config.status hardcodes its temp dir in the current directory
and assembles `subs1.awk` via `cat >>`, so it hits both behaviors at once.
The failure is deterministic per device: on one device config.status completed
normally and the full build finished; on another it failed 4/4 times.

## Decision rule

1. Confirm the diagnosis with the paired tests: plain `mkdir -p dir && chmod
   777 dir` then create/append inside — must succeed; `mktemp -d` then
   create — expected to fail.
2. Pre-create the config.status temp dir with `mkdir -p` + `chmod 777` and
   patch configure/config.status to use it via `${TMPDIR:-.}/cs`.
3. Sign any freshly built executable (`binary-sign-tool ... -selfSign 1`)
   before a make rule runs it.
4. Link a passthrough gettext stub archive for `g_libintl_*` references
   (see E508) — OHOS ships no libintl implementation.
5. Never start or diagnose a heavy build while another task is deleting or
   creating tens of thousands of files on the same distributed fs.

## gtk2 2.24.33 evidence

With the fixes above, gtk2 2.24.33 progressed through all configure checks
(BASE_DEPENDENCIES, CAIRO_BACKEND via the cairo-xlib alias, GLIB via the
gmodule-no-export-2.0 alias, Pango link) and compiled all sources against
glib 2.84 with zero deprecation errors. The only remaining link reference
(`g_libintl_gettext`) was resolved by the E508 passthrough stub archive.

## Boundary

This pattern does not remove the underlying policy restriction. If a device
denies O_APPEND or exec for the build task, autotools packages cannot be
built on it; provisioning must unify the policy, or such packages must be
built on a device of the permissive class.

## Related knowledge

E508 (gettext passthrough stub), E316 (HMDFS symlink materialization), and
the shared-fs inode-exhaustion diagnosis draft cover adjacent failure modes
observed in the same device session.
