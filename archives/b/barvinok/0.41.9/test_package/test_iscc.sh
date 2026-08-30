#!/system/bin/sh
set -eu

iscc_command=${1:-iscc}

"$iscc_command" >/dev/null <<'EOF'
r := sum { [[n] -> [i]] -> i : 0 <= i <= n };
assert(r == { [n] -> (1/2 * n + 1/2 * n^2) : n >= 0 });
EOF
