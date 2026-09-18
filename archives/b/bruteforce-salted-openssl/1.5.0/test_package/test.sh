#!/data/service/hnp/bin/bash
# test_package/test.sh — runs the 4 upstream crack-encrypted tests against the
# packaged bruteforce-salted-openssl binary (conanrun PATH).
set -eu

echo "[test] bruteforce-salted-openssl binary present"
command -v bruteforce-salted-openssl >/dev/null

# Upstream binary fixtures ship base64-encoded (encryptedN.dat.b64) so the PR
# diff patch (text-only) can carry them; decode to the exact upstream bytes.
for t in 1 2 3 4; do
    base64 -d encrypted${t}.dat.b64 > encrypted${t}.dat
done

for t in 1 2 3 4; do
    bash crack-encrypted${t}.sh
done

echo "✅ all 4 upstream crack tests passed"
