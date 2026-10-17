#!/system/bin/sh
set -eu
set -o pipefail
if [ "$#" -ne 3 ]; then
    printf "usage: %s PACKAGE_FOLDER MOVED_FOLDER TEST_R_SCRIPT\n" "$0" >&2
    exit 64
fi
package=$1
moved=$2
script=$3
if [ ! -x "$package/bin/R" ] || [ ! -x "$package/bin/Rscript" ]; then
    printf "missing R launchers in package: %s\n" "$package" >&2
    exit 66
fi
if [ ! -f "$script" ]; then
    printf "missing R test script: %s\n" "$script" >&2
    exit 66
fi
rm -rf "$moved"
mkdir -p "$moved"
cp -R "$package"/. "$moved"/
if grep -R -a -n -E "/storage/Users/currentUser|[.]conan2|[.]conan-build-r-base" "$moved"; then
    printf "non-relocatable build/cache path found in moved package\n" >&2
    exit 1
fi
unset R_HOME RHOME R_SHARE_DIR R_INCLUDE_DIR R_DOC_DIR CURL_CA_BUNDLE SSL_CERT_FILE SSL_CERT_DIR LD_LIBRARY_PATH
export PATH="/data/service/hnp/bin:/system/bin:/bin:/usr/bin"

# Make both the original target package and every original dependency package
# physically inaccessible while exercising the moved copy.  Always restore the
# cache permission, including failure paths.
cache_root=/storage/Users/currentUser/.conan2
harmonybrew_root=/storage/Users/currentUser/.harmonybrew
cache_mode=`stat -c %a "$cache_root"`
harmonybrew_mode=`stat -c %a "$harmonybrew_root"`
restore_hidden_roots() {
    chmod "$cache_mode" "$cache_root"
    chmod "$harmonybrew_mode" "$harmonybrew_root"
}
trap restore_hidden_roots EXIT HUP INT TERM
chmod 000 "$cache_root"
chmod 000 "$harmonybrew_root"

rhome=`"$moved/bin/R" RHOME`
test "$rhome" = "$moved/lib/R"
"$moved/bin/R" --vanilla --slave -f "$script"
"$moved/bin/Rscript" --vanilla -e "stopifnot(getRversion() == '4.5.1'); cat('R_BASE_RSCRIPT=PASS\n')"
for elf in `find "$moved" -type f`; do
    if /data/service/hnp/bin/llvm-readelf -h "$elf" >/dev/null 2>&1; then
        dyn=`/data/service/hnp/bin/llvm-readelf -d "$elf" 2>/dev/null`
        if printf "%s\n" "$dyn" | grep -E "RPATH|RUNPATH" | grep -E "/storage/Users|[.]conan2|[.]conan-build"; then
            exit 1
        fi
        for needed in `printf "%s\n" "$dyn" | sed -n "s/.*Shared library: \[\(.*\)\]/\1/p"`; do
            case "$needed" in
                libc.so|libdl.so|libm.so|librt.so|libpthread.so) ;;
                *) test -e "$moved/lib/R/lib/$needed" || {
                    printf "unsatisfied packaged ELF NEEDED: %s needs %s\n" "$elf" "$needed" >&2
                    exit 1
                } ;;
            esac
        done
    fi
done
restore_hidden_roots
trap - EXIT HUP INT TERM
printf "R_BASE_CACHE_MASK=PASS
"
printf "R_BASE_HARMONYBREW_MASK=PASS
"
printf "R_BASE_RELOCATION_NEGATIVE_TEST=PASS
"
