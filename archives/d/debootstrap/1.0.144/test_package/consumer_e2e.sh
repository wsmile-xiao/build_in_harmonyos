#!/bin/sh
# debootstrap consumer END-TO-END test (rule12): drives the REAL packaged
# `debootstrap --download-only` against a locally built minimal file://
# Debian archive and asserts the genuine downloads land on disk.
#
# Why this is a consumer use-case, not just assertions:
#   debootstrap itself performs every step through its own code paths —
#   download_release_indices (Release download + suite validation +
#   per-component/arch checksum bookkeeping), pkgdetails (perl: required /
#   base resolution and Packages parsing), download_debs (file:// just_get
#   copy + $SHA_SIZE checksum + size verification) and the debpaths output —
#   exactly the documented `debootstrap --download-only --variant=minbase`
#   consumer flow. The archive is a genuine apt-format mirror on disk
#   (Release + Packages indices, pool/ payloads).
#
# Adaptation notes for OHOS:
#   * variant=minbase resolves required = (Priority: required) + base = apt,
#     so a 2-stanza archive is a closed dependency set (no Depends lines).
#   * The mirror is file:// so downloads go through `cp` (just_get); wget
#     (the documented runtime dependency) only has to be present because the
#     standalone entry point checks it (NEEDWGET). If the host has no wget a
#     fail-fast stub that *aborts* on any network attempt is injected instead
#     of faking a download. `--arch arm64` is passed (no dpkg on OHOS).
#   * NO heredocs are used anywhere in this script, and every temp file lives
#     under the writable test_package cwd (OHOS /tmp is read-only).
set -eu

# Following test.sh: BIN_DIR/SHARE_DIR are the packaged artifact dirs.
BIN_DIR="$1"
SHARE_DIR="$2"
ARCH=arm64

case "$BIN_DIR" in
  [A-Za-z]:*)
    if command -v cygpath >/dev/null 2>&1; then
      BIN_DIR=$(cygpath -u "$BIN_DIR")
      SHARE_DIR=$(cygpath -u "$SHARE_DIR")
    fi
    ;;
esac

MAIN="$BIN_DIR/debootstrap"
export DEBOOTSTRAP_DIR="$SHARE_DIR"

# --- scratch area (writable: the test_package cwd, never /tmp) ------------
BASE="$PWD/db-e2e"
WORK="$BASE/scratch"
MIRROR="$BASE/mirror"
TARGET="$BASE/target"
rm -rf "$BASE"
mkdir -p "$MIRROR/dists/sid/main/binary-arm64" "$WORK"

# debootstrap needs a non-empty HOST_ARCH+HOST_OS before it will run (its
# WHATARCH guard): HOST_ARCH comes from dpkg/udpkg, falling back to an
# upstream-supported `arch` file in DEBOOTSTRAP_DIR, and HOST_OS from uname.
# The OHOS worker has no dpkg; Windows git-bash has neither dpkg nor a known
# uname -- both are handled by staging a writable data dir with an `arch`
# override file, so the download pipeline is exercisable everywhere CI runs.
if ! command -v dpkg >/dev/null 2>&1 && ! command -v udpkg >/dev/null 2>&1; then
  if [ ! -e "$SHARE_DIR/arch" ]; then
    mkdir -p "$WORK/share"
    cp -r "$SHARE_DIR/." "$WORK/share/"
    printf '%s\n' "$ARCH" > "$WORK/share/arch"
    export DEBOOTSTRAP_DIR="$WORK/share"
    echo "[e2e] no dpkg/udpkg on host; staged data dir with arch override: $DEBOOTSTRAP_DIR/arch"
  fi
fi

# --- minimal but genuine apt-format file:// Debian archive ----------------
# Deb files written with a sha256sum; debootstrap verifies Size + SHA256
# against the Packages/Release metadata we generate from the real files.
mk_deb() { printf 'dummy %s %s %s\n' "$1" "$2" "$3" > "$4"; }

mk_deb base-files 12.4 arm64 "$WORK/base-files.deb"
mk_deb apt 2.9.10 arm64 "$WORK/apt.deb"

get_sha256sum() { sha256sum "$1" | sed 's/ .*//'; }
get_size() { wc -c < "$1"; }

write_packages() {
  printf 'Package: base-files\nVersion: 12.4\nArchitecture: arm64\nPriority: required\nMulti-Arch: foreign\n'
  printf 'Filename: pool/main/b/base-files/base-files_12.4_arm64.deb\n'
  printf 'Size: %s\nSHA256: %s\n\n' "$(get_size "$WORK/base-files.deb")" "$(get_sha256sum "$WORK/base-files.deb")"
  printf 'Package: apt\nVersion: 2.9.10\nArchitecture: arm64\nPriority: standard\nMulti-Arch: foreign\n'
  printf 'Filename: pool/main/a/apt/apt_2.9.10_arm64.deb\n'
  printf 'Size: %s\nSHA256: %s\n\n' "$(get_size "$WORK/apt.deb")" "$(get_sha256sum "$WORK/apt.deb")"
} > "$MIRROR/dists/sid/main/binary-arm64/Packages"

write_packages

PACKAGES_FILE="$MIRROR/dists/sid/main/binary-arm64/Packages"
PACKAGES_SZ=$(get_size "$PACKAGES_FILE")
PACKAGES_SHA=$(get_sha256sum "$PACKAGES_FILE")

{
  printf 'Origin: debootstrap e2e-test archive\nLabel: debootstrap e2e-test\nSuite: sid\nCodename: sid\n'
  printf 'Date: Sat, 01 Jan 2022 00:00:00 UTC\nArchitectures: arm64\nComponents: main\n'
  printf 'Description: minimal local archive for the debootstrap consumer e2e test\n'
  printf 'SHA256:\n %s %s main/binary-arm64/Packages\n' "$PACKAGES_SHA" "$PACKAGES_SZ"
  if command -v sha1sum >/dev/null 2>&1; then
    printf 'SHA1:\n %s %s main/binary-arm64/Packages\n' \
      "$(sha1sum "$PACKAGES_FILE" | sed 's/ .*//')" "$PACKAGES_SZ"
  fi
} > "$MIRROR/dists/sid/Release"

# .deb payloads must physically exist under the paths recorded in Filename:.
mkdir -p "$MIRROR/pool/main/b/base-files" "$MIRROR/pool/main/a/apt"
cp "$WORK/base-files.deb" "$MIRROR/pool/main/b/base-files/base-files_12.4_arm64.deb"
cp "$WORK/apt.deb" "$MIRROR/pool/main/a/apt/apt_2.9.10_arm64.deb"

# --- wget: documented runtime dependency of the standalone entry point -----
# file:// mirrors are copied via `cp` (just_get), so the stub must never run;
# any real network attempt aborts loudly rather than being faked.
if ! command -v wget >/dev/null 2>&1; then
  if [ ! -x "$WORK/wget" ]; then
    printf '#!/bin/sh\n' > "$WORK/wget"
    printf 'echo "wget-shim: real wget is required for remote mirrors" >&2\n' >> "$WORK/wget"
    printf 'exit 3\n' >> "$WORK/wget"
    chmod +x "$WORK/wget"
  fi
  echo "[e2e] host has no wget; injected fail-fast wget shim (never needed for file://)"
  export PATH="$WORK:$PATH"
else
  echo "[e2e] using host wget: $(command -v wget)"
fi

# --- run the genuine consumer flow -----------------------------------------
echo "[e2e] mirror : $MIRROR"
echo "[e2e] target : $TARGET"
echo "[e2e] running: debootstrap --download-only --no-check-sig --arch arm64 --variant=minbase <suite> <target> <file://mirror>"
"$MAIN" --download-only --no-check-sig --arch arm64 --variant=minbase \
    sid "$TARGET" "file://$MIRROR"
echo "[e2e] debootstrap exited rc=0"

# --- assertion 1: debpaths lists both resolved packages ---------------------
DEBPATHS="$TARGET/debootstrap/debpaths"
if [ ! -f "$DEBPATHS" ]; then
  echo "[e2e] FAIL: $DEBPATHS not created"
  exit 1
fi
echo "[e2e] debpaths:"
cat "$DEBPATHS"

for want in "base-files " "apt "; do
  if grep -q "$want" "$DEBPATHS"; then
    echo "[e2e]   ok: debpath entry for ${want% }"
  else
    echo "[e2e] FAIL: debpaths missing entry for ${want% }"
    exit 1
  fi
done

# --- assertion 2: the .debs were genuinely downloaded + checksum-verified ---
count=0
while read -r _p dbpath; do
  if [ ! -f "$TARGET/$dbpath" ]; then
    echo "[e2e] FAIL: downloaded deb not on disk: $TARGET/$dbpath"
    exit 1
  fi
  echo "[e2e]   ok: downloaded $TARGET/$dbpath"
  count=$((count + 1))
done < "$DEBPATHS"

if [ "$count" -ne 2 ]; then
  echo "[e2e] FAIL: expected 2 downloaded debs, got $count"
  exit 1
fi

# --- assertion 3: indices were fetched through debootstrap (real cp code) ---
# download_style apt keeps indices under $TARGET/var/lib/apt/lists/ with
# mirror-encoded names and payloads under $TARGET/var/cache/apt/archives/.
for f in "$TARGET"/var/lib/apt/lists/*_dists_sid_Release; do
  if [ -f "$f" ]; then
    echo "[e2e]   ok: Release index fetched: ${f##*/}"
    found_rel=1
    break
  fi
done
if [ -z "${found_rel-}" ]; then
  echo "[e2e] FAIL: Release index not present under $TARGET/var/lib/apt/lists/"
  exit 1
fi
for f in "$TARGET"/var/lib/apt/lists/*_dists_sid_main_binary-arm64_Packages; do
  if [ -f "$f" ]; then found_pkg=1; break; fi
done
if [ -z "${found_pkg-}" ]; then
  echo "[e2e] FAIL: Packages index not present under $TARGET/var/lib/apt/lists/"
  exit 1
fi
echo "[e2e]   ok: Packages index fetched"

echo "[e2e] PASS"