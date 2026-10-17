#!/data/service/hnp/bin/bash
# test_package/test.sh — behaviour checks for the packaged debfoster executable.
#
# Invoked by test_package/conanfile.py inside the conanrun environment, so
# `debfoster` is the installed bin/debfoster.  Every check drives the real CLI
# and compares exit codes or exact stdout; no check is satisfied by the binary
# merely starting up.
#
# Contract the checks rely on:
#   - the dpkg status database, the keeper file and every option are selectable
#     from the command line (-c config, -k keeperfile, -o OPT=VAL), which is
#     what makes a self-contained test fixture possible;
#   - the query modes (-a keepers, -s orphans, -d depends, -e dependents,
#     -p providers, -r related) print deterministic, sorted answers on stdout
#     and exit 0; the package list of one query is printed on a single line;
#   - -r X answers "which packages would become orphaned if X were removed",
#     so a dependency that another package also needs is not reported;
#   - a keeper file is a flat list of one package per line, and a leading "-"
#     records a package the administrator refused;
#   - an unreadable dpkg status database exits 3, a bad option exits 1.
#
# The first stderr line of every invocation is
#   GC Warning: Failed to find PT_GNU_RELRO segment inside PT_LOAD region
# emitted by the statically linked Boehm collector of gc/8.2.12 on OHOS (a
# pre-existing property of that package; see notes.md).  Stdout is therefore
# what gets compared and stderr is deliberately not part of any assertion.

# Deliberately not "set -e": every check() call inspects the exit status of the
# command it just ran (debfoster is expected to return 1/3 on the error paths
# asserted below), and "set -e" would abort the script on the first such case
# instead of recording it.  Unset variables are still an error, and the final
# exit status is FAILED == 0, so a genuine failure cannot go unnoticed.
set -u

TMPBASE="${TMPDIR:-$HOME}"
WORK="$TMPBASE/debfoster-test-$$"
rm -rf "$WORK"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

PASSED=0
FAILED=0

check() {
    # $1 description, $2 actual, $3 expected
    if [ "$2" = "$3" ]; then
        PASSED=$((PASSED + 1))
        printf 'ok   %s\n' "$1"
    else
        FAILED=$((FAILED + 1))
        printf 'FAIL %s\n     expected: [%s]\n     actual:   [%s]\n' "$1" "$3" "$2"
    fi
}

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
# libfoo1 is pulled in by appbar, orphanbaz is pulled in by nothing and
# essentialpkg is protected by the Essential: default rule, so the interactive
# mode below must ask exactly one question.
cat > "$WORK/status" <<'EOF'
Package: libfoo1
Status: install ok installed
Priority: optional
Section: libs
Installed-Size: 100
Maintainer: Fixture <fixture@example.invalid>
Architecture: arm64
Version: 1.0-1
Provides: libfoo
Description: fixture library
 Fixture package used by the conan test_package of debfoster.

Package: appbar
Status: install ok installed
Priority: optional
Section: utils
Installed-Size: 50
Maintainer: Fixture <fixture@example.invalid>
Architecture: arm64
Version: 2.3-4
Depends: libfoo1 (>= 1.0)
Description: fixture application
 Fixture package used by the conan test_package of debfoster.

Package: orphanbaz
Status: install ok installed
Priority: optional
Section: misc
Installed-Size: 10
Maintainer: Fixture <fixture@example.invalid>
Architecture: arm64
Version: 0.1-1
Description: fixture orphan
 Fixture package used by the conan test_package of debfoster.

Package: essentialpkg
Status: install ok installed
Priority: required
Section: base
Essential: yes
Installed-Size: 20
Maintainer: Fixture <fixture@example.invalid>
Architecture: arm64
Version: 9.9-9
Description: fixture essential package
 Fixture package used by the conan test_package of debfoster.
EOF

# toolv needs libbar2 (satisfied: installed 2.5-1 >= 2.0) and libbaz, while
# needv9 also needs libbaz.  Removing toolv alone therefore orphans libbar2
# only, which is exactly what -r has to report.
cat > "$WORK/status-versioned" <<'EOF'
Package: libbar2
Status: install ok installed
Priority: optional
Section: libs
Installed-Size: 100
Maintainer: Fixture <fixture@example.invalid>
Architecture: arm64
Version: 2.5-1
Description: fixture bar library

Package: libbaz
Status: install ok installed
Priority: optional
Section: libs
Installed-Size: 30
Maintainer: Fixture <fixture@example.invalid>
Architecture: arm64
Version: 0.9-1
Description: fixture baz library

Package: toolv
Status: install ok installed
Priority: optional
Section: utils
Installed-Size: 50
Maintainer: Fixture <fixture@example.invalid>
Architecture: arm64
Version: 3.0-1
Depends: libbar2 (>= 2.0), libbaz
Description: fixture tool with a versioned dependency

Package: needv9
Status: install ok installed
Priority: optional
Section: utils
Installed-Size: 5
Maintainer: Fixture <fixture@example.invalid>
Architecture: arm64
Version: 1.0-1
Depends: libbaz
Description: fixture tool sharing a dependency
EOF

# Every external command is neutralised: the checks only exercise debfoster's
# own bookkeeping, never a package manager.
cat > "$WORK/debfoster.conf" <<EOF
DpkgStatus = $WORK/status
DpkgAvailable = $WORK/status
KeeperFile = $WORK/keepers
InstallCmd = /bin/true
RemoveCmd = /bin/true
InfoCmd = /bin/true
EOF

cat > "$WORK/debfoster-versioned.conf" <<EOF
DpkgStatus = $WORK/status-versioned
DpkgAvailable = $WORK/status-versioned
KeeperFile = $WORK/keepers-v
InstallCmd = /bin/true
RemoveCmd = /bin/true
InfoCmd = /bin/true
EOF

cat > "$WORK/nostatus.conf" <<EOF
DpkgStatus = $WORK/no-such-status
DpkgAvailable = $WORK/no-such-status
KeeperFile = $WORK/keepers
InstallCmd = /bin/true
RemoveCmd = /bin/true
InfoCmd = /bin/true
EOF

DF() { debfoster -c "$WORK/debfoster.conf" -k "$WORK/keepers" "$@"; }
DFV() { debfoster -c "$WORK/debfoster-versioned.conf" -k "$WORK/keepers-v" "$@"; }
keep() { printf '%s\n' "$@" > "$WORK/keepers"; }
: > "$WORK/keepers"
: > "$WORK/keepers-v"

# ---------------------------------------------------------------------------
# 1. self-reported version and option surface
# ---------------------------------------------------------------------------
check "debfoster --version reports 2.8" \
    "$(debfoster --version 2>/dev/null | sed -n 1p)" \
    "debfoster 2.8 -- Copyright (C) 2000,2001 Wessel Dankers."
check "-V is an alias of --version" \
    "$(debfoster -V 2>/dev/null | sed -n 1p)" \
    "debfoster 2.8 -- Copyright (C) 2000,2001 Wessel Dankers."
check "help prints a usage line" \
    "$(debfoster --help 2>/dev/null | grep -c '^Usage: .*debfoster \[-ck FILE\]')" "1"
check "help documents -k/--keeperfile" \
    "$(debfoster --help 2>/dev/null | grep -c -- '-k, --keeperfile FILE')" "1"
check "help documents -s/--show-orphans" \
    "$(debfoster --help 2>/dev/null | grep -c -- '-s, --show-orphans')" "1"
check "help documents all six query modes" \
    "$(debfoster --help 2>/dev/null | grep -cE -- '^-[adeprs], --show-')" "6"

# ---------------------------------------------------------------------------
# 2. argument and input error handling (exit codes are part of the contract)
# ---------------------------------------------------------------------------
debfoster --definitely-not-an-option > /dev/null 2>&1
check "unknown command line option exits 1" "$?" "1"
DF -o NoSuchOption=1 -a > /dev/null 2>&1
check "unknown -o option exits 1" "$?" "1"
DF -o NoEquals -a > /dev/null 2>&1
check "-o argument without '=' exits 1" "$?" "1"
debfoster -c "$WORK/nostatus.conf" -k "$WORK/keepers" -a > /dev/null 2>&1
check "unreadable dpkg status database exits 3" "$?" "3"

# ---------------------------------------------------------------------------
# 3. query modes against the fixture database
# ---------------------------------------------------------------------------
check "-a on an empty keeper file says so" \
    "$(DF -a 2>/dev/null)" "The keeper list is empty."
check "-s lists exactly the two unrequested packages" \
    "$(DF -s 2>/dev/null)" \
    "The following packages have been orphaned:
  appbar orphanbaz"
check "-d lists a package's dependencies" \
    "$(DF -d appbar 2>/dev/null)" \
    "Package appbar depends on:
  libfoo1"
check "-d reports an unknown package by name" \
    "$(DF -d nosuchpkg 2>/dev/null)" 'Not an installed package: "nosuchpkg"'
check "-p resolves a virtual dependency through Provides:" \
    "$(DF -p libfoo 2>/dev/null)" \
    "Dependency libfoo is met by:
  libfoo1"
check "-r reports the dependency that only appbar needs" \
    "$(DF -r appbar 2>/dev/null)" \
    "The following 1 packages are brought in by appbar:
  libfoo1"

keep appbar
check "-e resolves the keeper package that relies on a dependency" \
    "$(DF -e libfoo1 2>/dev/null)" \
    "The following 1 packages on the keeper list rely on libfoo1:
  appbar
Packages kept by default rules do not rely on libfoo1."

keep appbar libfoo1
check "-a echoes the keeper file contents sorted" \
    "$(DF -a 2>/dev/null)" \
    "The following packages are on the keeper list:
  appbar libfoo1"
check "-r reports nothing once the dependency is a keeper itself" \
    "$(DF -r appbar 2>/dev/null)" "No packages are brought in by appbar."

: > "$WORK/keepers"
check "-e on an empty keeper list reports no dependents" \
    "$(DF -e libfoo1 2>/dev/null)" \
    "Packages on the keeper list do not rely on libfoo1.
Packages kept by default rules do not rely on libfoo1."

# ---------------------------------------------------------------------------
# 4. interactive mode rewrites the keeper file (the core of the tool)
# ---------------------------------------------------------------------------
keep appbar
printf 'y\n' | DF > "$WORK/keep-y.log" 2>/dev/null
check "interactive keep answers exactly one question" \
    "$(grep -c '^Keep orphanbaz? \[Ynpsiuqx?\], \[H\]elp: Y$' "$WORK/keep-y.log")" "1"
check "essential and dependency packages are never asked about" \
    "$(grep -c '^Keep ' "$WORK/keep-y.log")" "1"
check "answering y records the package in the keeper file" \
    "$(cat "$WORK/keepers")" "appbar
orphanbaz"
check "the y answer is visible through -a" \
    "$(DF -a 2>/dev/null)" \
    "The following packages are on the keeper list:
  appbar orphanbaz"

keep appbar
printf 'n\n' | DF > "$WORK/keep-n.log" 2>/dev/null
check "answering n records the refusal with a leading dash" \
    "$(cat "$WORK/keepers")" "appbar
-orphanbaz"
check "a refused package disappears from -a" \
    "$(DF -a 2>/dev/null)" \
    "The following packages are on the keeper list:
  appbar"
check "a refused package is still reported as an orphan by -s" \
    "$(DF -s 2>/dev/null)" \
    "The following packages have been orphaned:
  orphanbaz"

# The keeper file is locked while debfoster runs (src/keepers.c); the lock has
# to be released again or every later invocation would fail.
DF -a > /dev/null 2>&1
check "the keeper file survives a repeated run" \
    "$(cat "$WORK/keepers")" "appbar
-orphanbaz"

# ---------------------------------------------------------------------------
# 5. dependency graph with versioned dependencies
# ---------------------------------------------------------------------------
check "-d lists both dependencies of toolv" \
    "$(DFV -d toolv 2>/dev/null)" \
    "Package toolv depends on:
  libbar2 libbaz"
check "-s finds the two packages nothing depends on" \
    "$(DFV -s 2>/dev/null)" \
    "The following packages have been orphaned:
  needv9 toolv"
check "-r reports only the single-use dependency of toolv" \
    "$(DFV -r toolv 2>/dev/null)" \
    "The following 1 packages are brought in by toolv:
  libbar2"
check "-r does not claim a dependency another package also needs" \
    "$(DFV -r needv9 2>/dev/null)" "No packages are brought in by needv9."
check "-e on the versioned fixture reports no dependents" \
    "$(DFV -e libbar2 2>/dev/null)" \
    "Packages on the keeper list do not rely on libbar2.
Packages kept by default rules do not rely on libbar2."

# ---------------------------------------------------------------------------
# 6. packaging layout: the configuration file shipped next to the binary
# ---------------------------------------------------------------------------
BINDIR="$(dirname "$(command -v debfoster)")"
PKGCONF="$BINDIR/../etc/debfoster.conf"
check "the packaged default configuration file is installed" \
    "$([ -f "$PKGCONF" ] && echo yes || echo no)" "yes"
check "the packaged configuration is accepted by -c and -o" \
    "$(debfoster -c "$PKGCONF" -o "DpkgStatus=$WORK/status" \
        -o "DpkgAvailable=$WORK/status" -k "$WORK/keepers" -s 2>/dev/null)" \
    "The following packages have been orphaned:
  orphanbaz"
# Without -c and -o the binary falls back to the prefix-absolute paths baked in
# at build time (<prefix>/var/lib/dpkg/status), which do not exist in a Conan
# package, so the run has to fail with the "unreadable database" code.
debfoster -k "$WORK/keepers" -a > /dev/null 2>&1
check "without -c the build-time prefix paths are used" "$?" "3"

printf '\nHMBS_TEST_SUMMARY discovered=%d passed=%d failed=%d skipped=0\n' \
    "$((PASSED + FAILED))" "$PASSED" "$FAILED"
[ "$FAILED" -eq 0 ]
