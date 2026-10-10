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
if grep -R -a -n -E "$HOME|[.]conan2|[.]conan-build-r-base" "$moved"; then
    printf "non-relocatable build/cache path found in moved package\n" >&2
    exit 1
fi
unset R_HOME RHOME R_SHARE_DIR R_INCLUDE_DIR R_DOC_DIR CURL_CA_BUNDLE SSL_CERT_FILE SSL_CERT_DIR LD_LIBRARY_PATH
export PATH="/data/service/hnp/bin:/system/bin:/bin:/usr/bin"

# Make both the original target package and every original dependency package
# physically inaccessible while exercising the moved copy.  Always restore the
# cache permission, including failure paths.
# Cache 根不得硬编码：CI worker 上 CONAN_HOME 可能被重定向（如 ~/.cache/conan2），
# 本机默认 ~/.conan2。目录不存在时跳过遮蔽（可移植性检查仍执行），
# 禁止在 set -e 下对缺失路径 stat 直接中止整个测试（PR #13992 教训）。
cache_root=${CONAN_HOME:-$HOME/.conan2}
harmonybrew_root=$HOME/.harmonybrew
cache_mode=
harmonybrew_mode=
if [ -d "$cache_root" ]; then
    cache_mode=`stat -c %a "$cache_root"`
fi
# layer 2 (harmonybrew 前缀根) 是纵深防御层的可选项：仅在该根实际存在时才遮蔽。
if [ -d "$harmonybrew_root" ]; then
    harmonybrew_mode=`stat -c %a "$harmonybrew_root"`
fi
restore_hidden_roots() {
    if [ -n "$cache_mode" ]; then
        chmod "$cache_mode" "$cache_root"
    fi
    if [ -n "$harmonybrew_mode" ]; then
        chmod "$harmonybrew_mode" "$harmonybrew_root"
    fi
}
trap restore_hidden_roots EXIT HUP INT TERM
if [ -n "$cache_mode" ]; then
    chmod 000 "$cache_root"
fi
if [ -n "$harmonybrew_mode" ]; then
    chmod 000 "$harmonybrew_root"
fi

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
if [ -n "$cache_mode" ]; then
    printf "R_BASE_CACHE_MASK=PASS
"
else
    printf "R_BASE_CACHE_MASK=SKIPPED (root absent: %s)
" "$cache_root"
fi
if [ -n "$harmonybrew_mode" ]; then
    printf "R_BASE_HARMONYBREW_MASK=PASS
"
else
    printf "R_BASE_HARMONYBREW_MASK=SKIPPED (root absent: %s)
" "$harmonybrew_root"
fi
printf "R_BASE_RELOCATION_NEGATIVE_TEST=PASS
"
