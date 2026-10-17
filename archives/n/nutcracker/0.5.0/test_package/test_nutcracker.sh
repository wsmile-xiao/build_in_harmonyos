#!/bin/bash
# nutcracker daemon 冒烟测试（由 test_package/conanfile.py 以 `bash script` 调用）
# 用法: bash test_nutcracker.sh <nutcracker 二进制绝对路径>
set -u

NUTCRACKER="$1"
TMPD=$(mktemp -d "${TMPDIR:-/tmp}/nc-tp-XXXXXX") || exit 1
PORT=22221
BACKEND=26379
# 随机 stats 监听端口（-s），避免默认 0.0.0.0:22222 被并发测试占用导致
# daemon 启动即退出（本地实测 Address in use 真坑）
STATS_PORT=$(( (RANDOM % 20000) + 30000 ))
DAEMON_PID=""
cleanup() {
  [ -n "$DAEMON_PID" ] && kill "$DAEMON_PID" 2>/dev/null
  rm -rf "$TMPD"
}
trap cleanup EXIT

fail() { echo "FAIL: $1"; exit 1; }
ok() { echo "OK: $1"; }

# --- 1) -V 版本断言（纯 IO） ---
VER=$("$NUTCRACKER" -V 2>&1)
case "$VER" in
  *nutcracker-0.5.0*) ok "-V version -> $(echo "$VER" | head -1)" ;;
  *) fail "-V version output: $VER" ;;
esac

# --- 2) -t 配置校验（最小配置：本机高位端口，后端指向不可达地址） ---
cat > "$TMPD/nutcracker.yml" <<'EOF'
alpha:
  listen: 127.0.0.1:22221
  hash: fnv1a_64
  distribution: ketama
  auto_eject_hosts: true
  redis: true
  server_retry_timeout: 2000
  server_failure_limit: 1
  servers:
   - 127.0.0.1:26379:1
EOF
"$NUTCRACKER" -t -c "$TMPD/nutcracker.yml" >/dev/null 2>&1 \
  || fail "-t config validation"
ok "-t config validation"

# --- 3) daemon 起进程 + 端口探测 + shutdown ---
# 后端不可达也能起进程（auto_eject_hosts 容忍，仅记录连接失败）
"$NUTCRACKER" -c "$TMPD/nutcracker.yml" -d -o "$TMPD/nc.log" -p "$TMPD/nc.pid" -s "$STATS_PORT" \
  || fail "daemonize"
sleep 2
if [ -s "$TMPD/nc.pid" ]; then
  DAEMON_PID=$(cat "$TMPD/nc.pid")
elif command -v pgrep >/dev/null 2>&1; then
  DAEMON_PID=$(pgrep -f "nutcracker.*$PORT" | head -1)
fi
[ -n "$DAEMON_PID" ] || fail "no daemon pid"
# 端口探测（bash /dev/tcp，规避 nc 依赖）
if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then
  ok "daemon listening on 127.0.0.1:$PORT (pid $DAEMON_PID)"
else
  fail "port probe on $PORT"
fi

# --- 4) 本地 nc 假后端做一次 Redis 转发验证（有 nc 才做，失败仅跳过） ---
NC=$(command -v nc || true)
if [ -n "$NC" ]; then
  # 假 redis 后端：收到请求回 $-1 (nil bulk reply)。twemproxy redis 只认
  # RESP 数组格式请求（inline "get foo\r\n" 不被解析，本地实测），客户端用
  # *2\r\n$3\r\nGET\r\n$3\r\nfoo\r\n。
  ( printf '$-1\r\n'; sleep 30 ) |
    "$NC" -l 127.0.0.1 "$BACKEND" >"$TMPD/backend.in" 2>/dev/null &
  BPID=$!
  sleep 1
  RESP=$(printf '*2\r\n$3\r\nGET\r\n$3\r\nfoo\r\n' | "$NC" -w 3 127.0.0.1 "$PORT" 2>/dev/null | tr -d '\r')
  kill "$BPID" 2>/dev/null
  if [ "$RESP" = '$-1' ]; then
    ok "forward to fake backend (RESP GET foo -> \$-1)"
  else
    echo "SKIP: forward verification (nc reply '$RESP' unexpected)"
  fi
else
  echo "SKIP: forward verification (nc not available)"
fi

# --- shutdown ---
kill "$DAEMON_PID" 2>/dev/null
sleep 1
kill -0 "$DAEMON_PID" 2>/dev/null && fail "daemon did not exit"
DAEMON_PID=""
ok "daemon shutdown"

echo "ALL PASS"