#!/bin/bash
# trojan 1.16.0 consumer test — real TLS wire behavior.
# usage: test_tls.sh <bindir-of-packaged-trojan>
set -e

# The packaged openssl binary embeds the OPENSSLDIR of the conan home it was
# built in, so its default openssl.cnf is absent here; point OPENSSL_CONF at
# /dev/null and let the explicit -subj/-batch arguments drive cert creation.
export OPENSSL_CONF=/dev/null

BINDIR="$1"
TROJAN="$BINDIR/trojan"
[ -x "$TROJAN" ] || { echo "trojan binary not found at $TROJAN"; exit 2; }

# 1. self-signed server certificate (same approach as upstream smoke)
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem \
    -days 1 -nodes -subj '/CN=trojan-test' -batch
[ -s cert.pem ] && [ -s key.pem ] || { echo "cert generation failed"; exit 3; }

# 2. minimal server config (password = SHA224("trojan-test"))
cat > server.json <<'CFG'
{
    "run_type": "server",
    "local_addr": "127.0.0.1",
    "local_port": 10443,
    "remote_addr": "127.0.0.1",
    "remote_port": 10080,
    "password": ["5e1394e5e8861c6a86ab64493a44c9efba20ad00155b864e15a0e1b9"],
    "log_level": 1,
    "ssl": {
        "cert": "cert.pem",
        "key": "key.pem",
        "key_password": "",
        "prefer_server_ciphers": true,
        "verify": true,
        "verify_host": "",
        "alpn": ["h2", "http/1.1"],
        "reuse_session": true,
        "session_ticket": true,
        "curves": "",
        "cipher": "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:AES128-GCM-SHA256"
    },
    "tcp": {"prefer_ipv4": true, "no_delay": true, "keep_alive": true, "fast_open": false, "fast_open_qlen": 20}
}
CFG

# 3. config validation code path must accept it
"$TROJAN" -t server.json

# 4. start the packaged server
nohup "$TROJAN" server.json > server.log 2>&1 &
PID=$!
trap 'kill -TERM $PID 2>/dev/null || true' EXIT

# 5. real TLS handshake against the running server
sleep 1
echo | openssl s_client -connect 127.0.0.1:10443 -CAfile cert.pem > s_client.log 2>&1
grep -q "Verify return code: 0" s_client.log || {
    echo "TLS handshake did not verify; s_client.log:"; tail -20 s_client.log; exit 4; }

echo "trojan TLS wire behavior verified on 127.0.0.1:10443"
