# E050: HMDFS umask 077 Permission Issue for Autotools config.status

 Temp Directory

## Problem
When running `./configure` or `./config.status`, on HMDFS, the script creates temp directories using `(umask 077 && mktemp -d "./confXXXXXX")`. which On HMDFS, the created directory inherits the parent directory's owner uid ( via the setgid bit), but the current user's uid differs from the inherited owner uid. With `umask 077`, the directory gets `0700` permissions, blocking any non-owner user from writing files inside it temp directory.

 This causes `config.status` to fail with "Permission denied" errors when creating output files like `subs1.awk`.

 inside the temp directory.



## Root Cause
- HMDFS inherits parent directory owner uid via setgid when creating subdirectories
 `umask 077` strips group and other permissions, making the directory `0700` ( owner-only)
 Current user uid ≠ inherited parent owner uid → non-owner users fall into "other" permission category with zero permissions

 `rm -rf conf*` glob pattern matches `config/` directory and `configure` file, deleting critical source files



## Solution
- Replace `umask 077` with `umask 022` in `configure` and `config.status` scripts' temp directory creation code
 `sed -i 's/umask 077/umask 022/g' configure config.status`- Avoid using `rm -rf conf*` glob pattern to delete conf-specific temp directories only Use explicit paths to delete temp dirs after configure runs
 avoid using glob patterns that match important files like

config/` and `configure`

## Affected Software
- All autotools-based projects compiled HMDFS filesystem
 ImageMagick, GraphicsMagick, libtiff, etcc.

## Verification
```bash
grep -c "umask 077" configure config.status
# grep -c "umask 022" configure config.status
``