#!/bin/bash
# install_perl_deps.sh — Install Perl runtime dependencies from CPAN
#
# Specio::Library::Path::Tiny requires Path::Tiny and Specio at runtime.
# These are not available on CI workers. This script downloads and
# installs them (and their dependencies) to a local lib directory.
#
# Usage: bash install_perl_deps.sh <perl_lib_dir>
# Output: Prints ONLY the PERL5LIB paths (colon-separated) to stdout.
#         All build output goes to stderr.

set -euo pipefail

PERL_LIB="${1:?Usage: install_perl_deps.sh <perl_lib_dir>}"
LOCAL_PERL5="${PERL_LIB}/lib/perl5"
LOCAL_ARCH="${LOCAL_PERL5}/aarch64-linux"

# If already installed (e.g., cached from previous run), skip
if [ -f "${LOCAL_PERL5}/Specio.pm" ] && [ -f "${LOCAL_PERL5}/Path/Tiny.pm" ]; then
    echo "${LOCAL_PERL5}:${LOCAL_ARCH}"
    exit 0
fi

mkdir -p "${PERL_LIB}"
WORK_DIR="${TMPDIR:-${HOME}/.tmp}/perl-cpan-build"
mkdir -p "${WORK_DIR}"

# Modules in dependency order (CPAN tarball URL|extracted dirname)
MODULES=(
  "https://cpan.metacpan.org/authors/id/H/HA/HAARG/Module-Runtime-0.018.tar.gz|Module-Runtime-0.018"
  "https://cpan.metacpan.org/authors/id/H/HA/HAARG/Role-Tiny-2.002005.tar.gz|Role-Tiny-2.002005"
  "https://cpan.metacpan.org/authors/id/H/HA/HAARG/Sub-Quote-2.006009.tar.gz|Sub-Quote-2.006009"
  "https://cpan.metacpan.org/authors/id/H/HA/HAARG/MRO-Compat-0.15.tar.gz|MRO-Compat-0.15"
  "https://cpan.metacpan.org/authors/id/E/ET/ETHER/Try-Tiny-0.32.tar.gz|Try-Tiny-0.32"
  "https://cpan.metacpan.org/authors/id/D/DO/DOY/Eval-Closure-0.14.tar.gz|Eval-Closure-0.14"
  "https://cpan.metacpan.org/authors/id/D/DR/DROLSKY/Module-Implementation-0.09.tar.gz|Module-Implementation-0.09"
  "https://cpan.metacpan.org/authors/id/A/AT/ATOOMIC/Clone-0.50.tar.gz|Clone-0.50"
  "https://cpan.metacpan.org/authors/id/N/NE/NEILB/Clone-PP-1.08.tar.gz|Clone-PP-1.08"
  "https://cpan.metacpan.org/authors/id/D/DR/DROLSKY/Devel-StackTrace-2.05.tar.gz|Devel-StackTrace-2.05"
  "https://cpan.metacpan.org/authors/id/R/RJ/RJBS/Test-Fatal-0.018.tar.gz|Test-Fatal-0.018"
  "https://cpan.metacpan.org/authors/id/D/DA/DAGOLDEN/Path-Tiny-0.150.tar.gz|Path-Tiny-0.150"
  "https://cpan.metacpan.org/authors/id/D/DR/DROLSKY/Specio-0.53.tar.gz|Specio-0.53"
)

for entry in "${MODULES[@]}"; do
    url="${entry%%|*}"
    dirname="${entry##*|}"
    tarball="${WORK_DIR}/${dirname}.tar.gz"
    src_dir="${WORK_DIR}/${dirname}"

    # Skip if already extracted
    if [ -f "${src_dir}/Makefile" ]; then
        cd "${src_dir}"
    else
        echo "Downloading ${dirname}..." >&2
        wget -O "${tarball}" "${url}" >&2
        cd "${WORK_DIR}"
        tar xzf "${tarball}"
        cd "${src_dir}"
    fi

    echo "Building ${dirname}..." >&2
    PERL5LIB="${LOCAL_PERL5}:${LOCAL_ARCH}" perl Makefile.PL INSTALL_BASE="${PERL_LIB}" >&2
    make -j1 >&2
    make install >&2
done

# ONLY this line goes to stdout — the PERL5LIB paths
echo "${LOCAL_PERL5}:${LOCAL_ARCH}"
