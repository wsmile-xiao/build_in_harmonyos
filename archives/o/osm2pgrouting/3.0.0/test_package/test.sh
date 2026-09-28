#!/data/service/hnp/bin/bash
# test_package/test.sh — functional verification of the osm2pgrouting CLI.
#
# R34: genuinely executes the installed osm2pgrouting binary and asserts its
# observable behaviour; it is not a print-only stub.  CI's destructive L1e
# check re-runs this script with the package's bin/ moved away and expects a
# failure, proving the test really depends on the built artifact.
#
# Usage: bash test.sh <package_folder> [stage_dir]
set -uo pipefail

PKG_ROOT="${1:?usage: test.sh <package_folder> [stage_dir]}"
# OHOS 拒绝执行**未签名**的 ELF：内核以 EPERM 拒绝，shell 报
# "Operation not permitted"、退出码 126。这与文件权限无关（chmod 755 无效），
# 也与目录挂载无关 —— 同一绝对路径下的已签名二进制就能跑。本包 install 出来的
# bin/osm2pgrouting 是我们自己 link 的，没有 .codesign 段，因此必须先签名。
# 先例（shell 侧同款）：archives/s/sound-juicer/3.40.0/test_package/test.sh；
# Python 侧：archives/g/glade/3.40.0/test_package/conanfile.py 的 _sign()。
# 签名只能对 staging 副本做 —— 就地改包内文件会污染已 compute 的包清单。
STAGE_DIR="${2:-${TMPDIR:-/data/storage/el2/base/cache}/osm2pgrouting-test}"
INSTALLED_BIN="$PKG_ROOT/bin/osm2pgrouting"
BIN="$STAGE_DIR/bin/osm2pgrouting"
SIGNER="/data/service/hnp/bin/binary-sign-tool"

# 每次先清掉上一次的 staging，否则 CI 的 L1e 破坏性检查（把包内 bin/ 移走
# 再跑一遍，要求失败）会命中残留副本而假通过。
rm -f "$BIN"
mkdir -p "$STAGE_DIR/bin"
if ! cp "$INSTALLED_BIN" "$BIN" 2>/dev/null; then
    echo "FAIL: cannot stage $INSTALLED_BIN (package bin/ missing?)"
    exit 1
fi
chmod 755 "$BIN" >/dev/null 2>&1
# 签名器必须裸环境调用：只要 LD_LIBRARY_PATH 里混进 OHOS SDK 的 llvm/lib，
# binary-sign-tool 的 `NEEDED libc++.so` 就会命中 `std::__1` 命名空间的那份
# libc++（系统那份是 `std::__h`），成串 "Error relocating ... symbol not found"、
# 退出码 127。本脚本稍后才把依赖目录写进 LD_LIBRARY_PATH，但 conanrun 环境本身
# 已经注入了一轮，所以这里显式 `env -u`。
# 见 knowledge/drafts/DRAFT-binary-sign-tool-buildenv-ldlibrarypath.md
if [ -x "$SIGNER" ]; then
    if ! env -u LD_LIBRARY_PATH "$SIGNER" sign -inFile "$BIN" -outFile "$BIN" -selfSign 1 >/dev/null 2>&1; then
        echo "FAIL: binary-sign-tool could not sign the staged binary"
        exit 1
    fi
else
    echo "WARN: $SIGNER not found; the binary will not be executable on OHOS"
fi

# osm2pgrouting links libexpat.so and libpq.so dynamically and libpqxx
# statically, so "the binary produces output at all" already proves the
# expat/libpq/libpqxx runtime stack was found by the loader.  VirtualRunEnv
# (env="conanrun") contributes the dependency directories and /system/lib64
# carries the platform libc++_shared.so; prepend rather than replace so
# neither is lost.  The package's own lib/ is appended as a belt-and-braces
# measure in case VirtualRunEnv only exposes the direct dependency.
export LD_LIBRARY_PATH="/system/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}:$PKG_ROOT/lib"

checks=0
failures=0
check() { # check <description> <0 = pass, non-0 = fail>
    checks=$((checks + 1))
    if [ "$2" -eq 0 ]; then
        echo "ok $checks - $1"
    else
        echo "not ok $checks - $1"
        failures=$((failures + 1))
    fi
}

matches() { # matches <haystack> <needle> -> 0 when <needle> is a literal substring
    case "$1" in
        *"$2"*) return 0 ;;
        *) return 1 ;;
    esac
}

run() { # run <args...> -> combined output in $OUT, exit status in $RC
    OUT="$("$BIN" "$@" 2>&1)"
    RC=$?
    # CI 只回传日志尾部若干千字符，失败时把真实输出回显成 TAP 注释行，
    # 否则"二进制根本没起来"和"输出文案对不上"在日志里长得一模一样。
    if [ "$RC" -ne 0 ]; then
        printf '# exec failed: rc=%s args=[%s]\n' "$RC" "$*"
        printf '# captured output: %s\n' "$OUT"
    fi
}

# ── 1. the installed artifact is a runnable tool ─────────────────────
[ -x "$BIN" ]
check "bin/osm2pgrouting is staged out of the package cache and executable" $?

# ── 2..4. --version / -v report the 3.0.0 release ────────────────────
run --version
[ "$RC" -eq 0 ]
check "--version exits 0" $?
matches "$OUT" "This is osm2pgrouting Version 3.0.0"
check "--version prints the 3.0.0 version string (boost::program_options parsed it)" $?

run -v
matches "$OUT" "This is osm2pgrouting Version 3.0.0"
check "-v short form prints the same version string" $?

# ── 5..7. --help dumps the full option description ───────────────────
run --help
[ "$RC" -eq 0 ]
check "--help exits 0" $?
matches "$OUT" "Allowed options"
check "--help prints the 'Allowed options' description header" $?
matches "$OUT" "--file" && matches "$OUT" "--dbname"
check "--help documents both required options (--file and --dbname)" $?

# ── 8..10. missing required options: upstream's required_option path ──
run
[ "$RC" -eq 0 ]
check "invocation with no arguments exits 0 (upstream returns 0 on required_option)" $?
matches "$OUT" "required"
check "no-argument run reports the missing required option" $?
matches "$OUT" "Allowed options"
check "no-argument run falls back to dumping the option description" $?

# ── 11..12. unrecognised option is rejected ──────────────────────────
run --definitely-not-an-option
[ "$RC" -ne 0 ]
check "unknown option exits non-zero" $?
matches "$OUT" "unrecognised" || matches "$OUT" "unrecognized"
check "unknown option is reported as unrecognised" $?

# ── 13..16. the boost -> libpqxx -> libpq stack really runs ──────────
# Nothing listens on loopback port 1, so `pqxx::connection` is constructed and
# libpq performs a real connect() that gets refused.  This exercises the whole
# stack end to end without needing a live PostgreSQL/PostGIS server (which the
# CI worker does not have).
PROBE_DB="osm2pgrouting_ci_probe"
run -f /dev/null -d "$PROBE_DB" -h 127.0.0.1 -p 1
matches "$OUT" "COMMAND LINE CONFIGURATION"
check "the parsed command line is echoed back (process_command_line ran)" $?
matches "$OUT" "Filename = /dev/null" && matches "$OUT" "dbname = $PROBE_DB"
check "the -f/-d values passed through boost's variables_map intact" $?
matches "$OUT" "Testing database connection: $PROBE_DB"
check "the tool reaches the connection stage (pqxx::connection was constructed)" $?
[ "$RC" -eq 1 ]
check "the failed database connection exits 1" $?

# ── 17..21. installed routing configuration + license ────────────────
for f in \
    share/osm2pgrouting/mapconfig.xml \
    share/osm2pgrouting/mapconfig_for_cars.xml \
    share/osm2pgrouting/mapconfig_for_bicycles.xml \
    share/osm2pgrouting/mapconfig_for_pedestrian.xml \
    share/osm2pgrouting/COPYING ; do
    [ -s "$PKG_ROOT/$f" ]
    check "installed file present and non-empty: $f" $?
done

# The shipped configuration must be a well-formed document: the XML
# declaration has to be there, which is exactly what expat's SAX parser
# (xml::XMLParser) consumes.
CONF_HEAD="$(head -c 5 "$PKG_ROOT/share/osm2pgrouting/mapconfig_for_cars.xml" 2>/dev/null)"
[ "$CONF_HEAD" = "<?xml" ]
check "mapconfig_for_cars.xml starts with an XML declaration" $?

echo "assertions: $checks, failures: $failures"
[ "$failures" -eq 0 ] || exit 1
echo "ALL TESTS PASSED"
