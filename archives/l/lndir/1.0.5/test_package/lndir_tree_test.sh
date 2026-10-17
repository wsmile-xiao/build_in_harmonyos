#!/bin/sh
# lndir_tree_test.sh — functional test for the packaged lndir binary.
#
# Usage: lndir_tree_test.sh <lndir_bin> <work_dir>
#
# Creates a small source directory tree, runs lndir to build a shadow tree of
# symlinks, then verifies:
#   1. regular files in the source become symlinks in the shadow tree
#   2. subdirectories in the source are real directories in the shadow tree
#   3. the symlinks point at the correct source files
#   4. revision-control dirs (.git/.svn/CVS/...) are skipped by default
#   5. the -ignorelinks/-silent/-withrevinfo flags are accepted (exit 0)
#
# Exits non-zero on any mismatch (so conan test fails). Never swallows errors.

set -eu

LNDIR="$1"
WORK="$2"

if [ ! -x "$LNDIR" ]; then
    echo "[fail] lndir binary not executable: $LNDIR" >&2
    exit 1
fi

SRC="$WORK/source"
SHADOW="$WORK/shadow"

# --- Build a small source tree -------------------------------------------
mkdir -p "$SRC/subdir/nested" "$SRC/emptydir"
printf 'hello top\n' > "$SRC/topfile.txt"
printf 'nested file\n' > "$SRC/subdir/nested_file.txt"
printf 'sibling\n' > "$SRC/subdir/sibling.txt"
# revision-control dirs that lndir must skip by default
mkdir -p "$SRC/.git/objects" "$SRC/CVS" "$SRC/.svn"
printf 'rubbish\n' > "$SRC/.git/config"
printf 'entries\n' > "$SRC/CVS/Entries"
# A file ending in ~ is skipped by lndir (backup-file heuristic)
printf 'backup\n' > "$SRC/scratch~"

# --- Run lndir: create shadow tree of symlinks ---------------------------
mkdir -p "$SHADOW"
"$LNDIR" -silent "$SRC" "$SHADOW" >"$WORK/lndir_stdout.log" 2>&1 || {
    echo "[fail] lndir exited non-zero" >&2
    cat "$WORK/lndir_stdout.log" >&2
    exit 1
}

# --- Verify the shadow tree ------------------------------------------------

# 1. regular file -> symlink pointing at the source file
assert_symlink() {
    shadow="$1"; src="$2"; name="$3"
    if [ -L "$shadow" ]; then
        target=$(readlink -- "$shadow")
        # lndir may use absolute or relative targets; resolve and compare.
        case "$target" in
            /*) resolved="$target" ;;
            *)  resolved=$(cd "$(dirname -- "$shadow")" && cd "$(dirname -- "$target")" && pwd)/"$(basename -- "$target")" ;;
        esac
        if [ "$resolved" = "$src" ]; then
            echo "[ok] $name: symlink -> $src"
            return 0
        fi
        echo "[fail] $name: symlink target mismatch (got $target -> $resolved, want $src)" >&2
        exit 1
    fi
    echo "[fail] $name: expected a symlink, got: $(ls -ld "$shadow" 2>/dev/null || echo missing)" >&2
    exit 1
}

# 2. directory -> real directory (not a symlink)
assert_real_dir() {
    dir="$1"; name="$2"
    if [ -d "$dir" ] && [ ! -L "$dir" ]; then
        echo "[ok] $name: real directory"
        return 0
    fi
    echo "[fail] $name: expected a real directory" >&2
    exit 1
}

# 3. absence assertion
assert_absent() {
    path="$1"; name="$2"
    if [ -e "$path" ] || [ -L "$path" ]; then
        echo "[fail] $name: $path should not exist (lndir should have skipped it)" >&2
        exit 1
    fi
    echo "[ok] $name: absent (skipped)"
}

echo "--- verifying shadow tree ---"
assert_real_dir "$SHADOW/subdir" "subdir"
assert_real_dir "$SHADOW/subdir/nested" "subdir/nested"
assert_real_dir "$SHADOW/emptydir" "emptydir"
assert_symlink "$SHADOW/topfile.txt" "$SRC/topfile.txt" "topfile.txt"
assert_symlink "$SHADOW/subdir/nested_file.txt" "$SRC/subdir/nested_file.txt" "nested_file.txt"
assert_symlink "$SHADOW/subdir/sibling.txt" "$SRC/subdir/sibling.txt" "sibling.txt"

# 4. revision-control dirs + backup files must be skipped by default
assert_absent "$SHADOW/.git" ".git (skipped)"
assert_absent "$SHADOW/CVS" "CVS (skipped)"
assert_absent "$SHADOW/.svn" ".svn (skipped)"
assert_absent "$SHADOW/scratch~" "backup file ~ (skipped)"

# 5. the symlink contents must resolve to the real source bytes
got=$(cat "$SHADOW/topfile.txt")
if [ "$got" = "hello top" ]; then
    echo "[ok] topfile.txt symlink resolves to source content"
else
    echo "[fail] topfile.txt symlink content mismatch (got '$got')" >&2
    exit 1
fi

# 6. flags accepted (lndir must not reject -ignorelinks/-silent/-withrevinfo).
#    lndir requires the target dir to pre-exist, so mkdir it first.
flag_work="$WORK/flags"
mkdir -p "$flag_work/shadow1" "$flag_work/shadow2"
"$LNDIR" -silent -ignorelinks "$SRC" "$flag_work/shadow1" >"$WORK/flag1.log" 2>&1 || {
    echo "[fail] lndir rejected -silent -ignorelinks" >&2
    cat "$WORK/flag1.log" >&2
    exit 1
}
"$LNDIR" -withrevinfo "$SRC" "$flag_work/shadow2" >"$WORK/flag2.log" 2>&1 || {
    echo "[fail] lndir rejected -withrevinfo" >&2
    cat "$WORK/flag2.log" >&2
    exit 1
}
# With -withrevinfo, .git should now be present in the shadow tree
if [ -d "$flag_work/shadow2/.git" ]; then
    echo "[ok] -withrevinfo retained .git"
else
    echo "[fail] -withrevinfo should have retained .git" >&2
    exit 1
fi

# 7. lndir must refuse identical from/to dirs (returns non-zero)
mkdir -p "$WORK/identical"
if "$LNDIR" "$WORK/identical" "$WORK/identical" >/dev/null 2>&1; then
    echo "[fail] lndir accepted identical from/to directories" >&2
    exit 1
fi
echo "[ok] lndir rejects identical from/to directories"

echo "--- ALL CHECKS PASSED ---"
