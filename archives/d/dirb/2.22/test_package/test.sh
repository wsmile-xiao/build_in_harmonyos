#!/bin/sh
# dirb 2.22 test_package：真实功能验证
# 1) 无参运行 → 打印 usage 后按上游约定以非零码退出（exit(-1)），断言 banner
# 2) 本地 loopback HTTP 服务（python3 http.server）+ 预置词表真实扫描，
#    断言发现预置目录 admin/、backup/
#
# 全部运行产物（wordlist/scan 输出/server 日志）只写进 mktemp 临时目录，
# 不污染 test_package 源目录（conan 2 的 test() 以源目录为 cwd 运行）。

set -u

DIRB_BIN=$(command -v dirb)
if [ -z "$DIRB_BIN" ]; then
    echo "FAIL: dirb not found in PATH"
    exit 1
fi
echo "dirb binary: $DIRB_BIN"

# ── 1) usage 冒烟 ──
out=$("$DIRB_BIN" 2>&1)
rc=$?
echo "$out" | grep -q "DIRB" || { echo "FAIL: no usage banner on no-arg run"; exit 1; }
if [ "$rc" -eq 0 ]; then
    echo "FAIL: no-arg run unexpectedly exited 0"
    exit 1
fi
echo "usage smoke test: OK (rc=$rc, non-zero as expected)"

# ── 2) 真实扫描 loopback HTTP 服务 ──
if ! command -v python3 >/dev/null 2>&1; then
    echo "FAIL: python3 not found in PATH"
    exit 1
fi

WORK=$(mktemp -d) || exit 1
SRV=
trap 'kill "$SRV" 2>/dev/null; rm -rf "$WORK"' EXIT
cd "$WORK"

DOCROOT="$WORK/docroot"
mkdir -p "$DOCROOT/admin" "$DOCROOT/backup"
echo "dirb-e2e-secret-admin" > "$DOCROOT/admin/index.html"
echo "dirb-e2e-secret-backup" > "$DOCROOT/backup/index.html"
printf 'admin\nbackup\nnothing_here_xyz\n' > wordlist.txt

PORT=$(( ($$ % 15000) + 40000 ))
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$DOCROOT" > server.log 2>&1 &
SRV=$!

# 等服务就绪（最多 ~10s；curl 来自 conan 依赖包，已在 conanrun PATH）
i=0
while [ "$i" -lt 50 ]; do
    if command -v curl >/dev/null 2>&1; then
        if curl -s -o /dev/null "http://127.0.0.1:$PORT/"; then
            break
        fi
    else
        sleep 1
        break
    fi
    i=$(( i + 1 ))
done

"$DIRB_BIN" "http://127.0.0.1:$PORT/" wordlist.txt > dirb_scan.out 2>&1
scan_rc=$?
kill "$SRV" 2>/dev/null

echo "--- dirb scan output (rc=$scan_rc) ---"
cat dirb_scan.out
echo "---------------------------------------"

found_admin=$(grep -c "admin" dirb_scan.out)
found_backup=$(grep -c "backup" dirb_scan.out)

if [ "$found_admin" -eq 0 ]; then
    echo "FAIL: dirb did not discover /admin (scan_rc=$scan_rc)"
    exit 1
fi
if [ "$found_backup" -eq 0 ]; then
    echo "FAIL: dirb did not discover /backup (scan_rc=$scan_rc)"
    exit 1
fi

echo "dirb loopback scan test: PASS (admin/backup discovered)"
exit 0
