# E081: HMDFS setgid Directory Prevents File Creation Under umask 077

## Summary

On HarmonyOS (HMDFS filesystem), `umask 077` combined with `mktemp -d` creates directories with `drwx--S---` permissions. The setgid bit (S) is always inherited on HMDFS, and when combined with no group permissions, even the directory owner cannot create files inside it. This causes `configure` and `config.status` to fail with "Permission denied" when they try to write temporary files.

## Error Pattern

```
./config.status: line 821: ./confXXXXXX/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

or during configure:

```
./config.status[982]: can't create ./confXXXXXX/subs1.awk: Permission denied
```

## Root Cause

1. HMDFS filesystem always applies the setgid bit to newly created directories
2. When `umask 077` is applied, `mktemp -d "./confXXXXXX"` creates a directory with permissions `drwx--S---` (2700)
3. The setgid bit without group execute (`S` instead of `s`) prevents file creation inside the directory, even for the owner
4. This is different from standard Linux where the owner always has write access regardless of group permissions

## Verification

```bash
# This FAILS on HMDFS:
cd ~/tmp && (umask 077 && tmp=$(mktemp -d "./confXXXXXX") && echo test > "$tmp/testfile")
# zsh:1: permission denied: ./confXXXXXX/testfile

# This SUCCEEDS on HMDFS (umask 022 gives group read/execute):
cd ~/tmp && (umask 022 && tmp=$(mktemp -d "./confXXXXXX") && echo test > "$tmp/testfile")
# test
```

## Solution

Replace `umask 077` with `umask 022` in the configure and config.status scripts:

```bash
sed -i 's/umask 077/umask 022/g' configure config.status
```

This affects two locations in each file:
- The `mktemp -d` temp directory creation line
- The fallback `mkdir "$tmp"` line

## Affected Software

Any autotools-based software that uses `configure`/`config.status` on HarmonyOS, including but not limited to:
- libdbi
- Any software with autoconf-generated configure scripts

## Related

- E002: /tmp read-only on HarmonyOS
- E007: config.guess/config.sub platform detection
- E046: chmod not effective on HMDFS (setgid cannot be removed)