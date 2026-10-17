#!/usr/bin/env bash
set -euo pipefail

REDIS_SERVER="${REDIS_SERVER:-redis-server}"
REDIS_SENTINEL="${REDIS_SENTINEL:-redis-sentinel}"
REDIS_CLI="${REDIS_CLI:-redis-cli}"
REDIS_BENCHMARK="${REDIS_BENCHMARK:-redis-benchmark}"
REDIS_CHECK_RDB="${REDIS_CHECK_RDB:-redis-check-rdb}"
REDIS_CHECK_AOF="${REDIS_CHECK_AOF:-redis-check-aof}"

BASE_PORT=$((22000 + ($$ % 5000)))
MAIN_PORT=$BASE_PORT
RDB_PORT=$((BASE_PORT + 1))
AOF_PORT=$((BASE_PORT + 2))
MASTER_PORT=$((BASE_PORT + 3))
REPLICA_PORT=$((BASE_PORT + 4))
SENTINEL_PORT=$((BASE_PORT + 5))
CLUSTER_1_PORT=$((BASE_PORT + 6))
CLUSTER_2_PORT=$((BASE_PORT + 7))
CLUSTER_3_PORT=$((BASE_PORT + 8))
WORK_ROOT="${TMPDIR:-$PWD}"
WORK_DIR="$WORK_ROOT/redis-test-$$"
PORTS=""
ASSERTIONS=0

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

assert_eq() {
    expected=$1
    actual=$2
    label=$3
    [ "$actual" = "$expected" ] || fail "$label: expected '$expected', got '$actual'"
    ASSERTIONS=$((ASSERTIONS + 1))
}

assert_contains() {
    value=$1
    needle=$2
    label=$3
    case "$value" in
        *"$needle"*) ;;
        *) fail "$label: '$needle' not found in '$value'" ;;
    esac
    ASSERTIONS=$((ASSERTIONS + 1))
}

assert_file() {
    [ -s "$1" ] || fail "$2: missing or empty file $1"
    ASSERTIONS=$((ASSERTIONS + 1))
}

assert_command() {
    command -v "$1" >/dev/null 2>&1 || fail "packaged command not found: $1"
    ASSERTIONS=$((ASSERTIONS + 1))
}

cli_at() {
    port=$1
    shift
    "$REDIS_CLI" -h 127.0.0.1 -p "$port" --raw "$@"
}

wait_ready() {
    port=$1
    attempt=0
    while [ "$attempt" -lt 100 ]; do
        reply=$(cli_at "$port" ping 2>/dev/null || true)
        [ "$reply" = "PONG" ] && return 0
        attempt=$((attempt + 1))
        sleep 0.1
    done
    return 1
}

wait_info_value() {
    port=$1
    section=$2
    key=$3
    expected=$4
    attempt=0
    while [ "$attempt" -lt 300 ]; do
        value=$(cli_at "$port" info "$section" 2>/dev/null | tr -d '\r' | sed -n "s/^${key}://p" || true)
        [ "$value" = "$expected" ] && return 0
        attempt=$((attempt + 1))
        sleep 0.1
    done
    return 1
}

wait_cluster_state() {
    port=$1
    expected=$2
    attempt=0
    while [ "$attempt" -lt 300 ]; do
        value=$(cli_at "$port" cluster info 2>/dev/null | tr -d '\r' | sed -n 's/^cluster_state://p' || true)
        [ "$value" = "$expected" ] && return 0
        attempt=$((attempt + 1))
        sleep 0.1
    done
    return 1
}

start_server() {
    port=$1
    dir=$2
    shift 2
    mkdir -p "$dir"
    "$REDIS_SERVER" \
        --bind 127.0.0.1 \
        --protected-mode no \
        --port "$port" \
        --save "" \
        --appendonly no \
        --daemonize yes \
        --pidfile "$dir/redis.pid" \
        --dir "$dir" \
        --logfile "$dir/redis.log" \
        "$@"
    PORTS="$PORTS $port"
    wait_ready "$port" || {
        cat "$dir/redis.log" >&2 || true
        fail "redis-server on port $port did not become ready"
    }
}

stop_server() {
    cli_at "$1" shutdown nosave >/dev/null 2>&1 || true
    sleep 0.1
}

cleanup() {
    for port in $PORTS; do
        cli_at "$port" shutdown nosave >/dev/null 2>&1 || true
    done
    if [ -d "$WORK_DIR" ]; then
        find "$WORK_DIR" -name '*.pid' -type f 2>/dev/null | while IFS= read -r pidfile; do
            pid=$(cat "$pidfile" 2>/dev/null || true)
            [ -z "$pid" ] || kill "$pid" >/dev/null 2>&1 || true
        done
    fi
}
trap cleanup EXIT INT TERM
mkdir -p "$WORK_DIR"

for command_name in redis-server redis-sentinel redis-cli redis-benchmark redis-check-rdb redis-check-aof; do
    assert_command "$command_name"
done

server_version=$($REDIS_SERVER --version)
assert_contains "$server_version" "v=8.2.7" "redis-server version"
cli_version=$($REDIS_CLI --version)
assert_contains "$cli_version" "8.2.7" "redis-cli version"

start_server "$MAIN_PORT" "$WORK_DIR/main"
assert_eq "PONG" "$(cli_at "$MAIN_PORT" ping)" "PING"

assert_eq "OK" "$(cli_at "$MAIN_PORT" set harmony:string value)" "SET"
assert_eq "value" "$(cli_at "$MAIN_PORT" get harmony:string)" "GET"
assert_eq "8" "$(cli_at "$MAIN_PORT" append harmony:string '-os')" "APPEND"
assert_eq "value-os" "$(cli_at "$MAIN_PORT" get harmony:string)" "GET after APPEND"
assert_eq "1" "$(cli_at "$MAIN_PORT" incr harmony:counter)" "INCR"
assert_eq "11" "$(cli_at "$MAIN_PORT" incrby harmony:counter 10)" "INCRBY"
assert_eq "OK" "$(cli_at "$MAIN_PORT" set harmony:bits x)" "SET bit source"
assert_eq "4" "$(cli_at "$MAIN_PORT" bitcount harmony:bits)" "BITCOUNT"

assert_eq "2" "$(cli_at "$MAIN_PORT" hset harmony:hash field1 one field2 two)" "HSET"
assert_eq "two" "$(cli_at "$MAIN_PORT" hget harmony:hash field2)" "HGET"
assert_eq "7" "$(cli_at "$MAIN_PORT" hincrby harmony:hash count 7)" "HINCRBY"
assert_eq "3" "$(cli_at "$MAIN_PORT" hlen harmony:hash)" "HLEN"

assert_eq "3" "$(cli_at "$MAIN_PORT" rpush harmony:list one two three)" "RPUSH"
assert_eq "one" "$(cli_at "$MAIN_PORT" lindex harmony:list 0)" "LINDEX first"
assert_eq "three" "$(cli_at "$MAIN_PORT" lindex harmony:list -1)" "LINDEX last"
assert_eq "one" "$(cli_at "$MAIN_PORT" lpop harmony:list)" "LPOP"

assert_eq "3" "$(cli_at "$MAIN_PORT" sadd harmony:set red green blue)" "SADD"
assert_eq "1" "$(cli_at "$MAIN_PORT" sismember harmony:set green)" "SISMEMBER"
assert_eq "3" "$(cli_at "$MAIN_PORT" scard harmony:set)" "SCARD"
assert_eq "2" "$(cli_at "$MAIN_PORT" sadd harmony:set2 green black)" "second SADD"
assert_eq "1" "$(cli_at "$MAIN_PORT" sinterstore harmony:intersection harmony:set harmony:set2)" "SINTERSTORE"
assert_eq "green" "$(cli_at "$MAIN_PORT" spop harmony:intersection)" "SPOP"

assert_eq "2" "$(cli_at "$MAIN_PORT" zadd harmony:zset 1 one 2 two)" "ZADD"
assert_eq "two" "$(cli_at "$MAIN_PORT" zrange harmony:zset -1 -1)" "ZRANGE"
assert_eq "5" "$(cli_at "$MAIN_PORT" zincrby harmony:zset 3 two)" "ZINCRBY"
assert_eq "0" "$(cli_at "$MAIN_PORT" zrank harmony:zset one)" "ZRANK"

stream_id=$(cli_at "$MAIN_PORT" xadd harmony:stream '*' field value)
assert_contains "$stream_id" "-" "XADD id"
assert_eq "1" "$(cli_at "$MAIN_PORT" xlen harmony:stream)" "XLEN"
assert_eq "OK" "$(cli_at "$MAIN_PORT" xgroup create harmony:stream harmony-group 0)" "XGROUP CREATE"
stream_reply=$(cli_at "$MAIN_PORT" xreadgroup group harmony-group consumer count 1 streams harmony:stream '>' 2>/dev/null)
assert_contains "$stream_reply" "value" "XREADGROUP"
assert_eq "1" "$(cli_at "$MAIN_PORT" xack harmony:stream harmony-group "$stream_id")" "XACK"

assert_eq "1" "$(cli_at "$MAIN_PORT" pfadd harmony:hll alpha beta gamma)" "PFADD"
assert_eq "3" "$(cli_at "$MAIN_PORT" pfcount harmony:hll)" "PFCOUNT"
assert_eq "2" "$(cli_at "$MAIN_PORT" geoadd harmony:geo 13.361389 38.115556 Palermo 15.087269 37.502669 Catania)" "GEOADD"
assert_eq "2" "$(cli_at "$MAIN_PORT" geosearchstore harmony:geo-result harmony:geo frommember Palermo byradius 200 km)" "GEOSEARCHSTORE"

printf 'MULTI\nINCR harmony:tx\nINCR harmony:tx\nEXEC\n' | "$REDIS_CLI" -h 127.0.0.1 -p "$MAIN_PORT" --raw >/dev/null
assert_eq "2" "$(cli_at "$MAIN_PORT" get harmony:tx)" "MULTI/EXEC"
assert_eq "lua-ok" "$(cli_at "$MAIN_PORT" eval 'return redis.call("SET",KEYS[1],ARGV[1]) and ARGV[1]' 1 harmony:lua lua-ok)" "EVAL"
library_code='#!lua name=harmony
redis.register_function("answer", function() return 42 end)'
assert_eq "harmony" "$(cli_at "$MAIN_PORT" function load replace "$library_code")" "FUNCTION LOAD"
assert_eq "42" "$(cli_at "$MAIN_PORT" fcall answer 0)" "FCALL"

assert_eq "OK" "$(cli_at "$MAIN_PORT" acl setuser harmony-user on '>harmony-pass' '~*' '+@all')" "ACL SETUSER"
assert_eq "PONG" "$($REDIS_CLI -h 127.0.0.1 -p "$MAIN_PORT" --raw --user harmony-user --pass harmony-pass --no-auth-warning ping)" "ACL authenticated PING"
bad_auth=$($REDIS_CLI -h 127.0.0.1 -p "$MAIN_PORT" --raw --user harmony-user --pass wrong --no-auth-warning ping 2>&1 || true)
assert_contains "$bad_auth" "AUTH failed" "ACL rejects wrong password"
assert_eq "1" "$(cli_at "$MAIN_PORT" acl deluser harmony-user)" "ACL DELUSER"

assert_eq "OK" "$(cli_at "$MAIN_PORT" set harmony:ttl value px 200)" "SET PX"
sleep 0.4
assert_eq "0" "$(cli_at "$MAIN_PORT" exists harmony:ttl)" "key expiration"
wrong_type=$(cli_at "$MAIN_PORT" lpush harmony:string bad 2>&1 || true)
assert_contains "$wrong_type" "WRONGTYPE" "wrong-type negative path"

block_output="$WORK_DIR/blocking.out"
cli_at "$MAIN_PORT" blpop harmony:blocking 3 >"$block_output" &
block_pid=$!
sleep 0.2
assert_eq "1" "$(cli_at "$MAIN_PORT" rpush harmony:blocking payload)" "blocking list producer"
wait "$block_pid"
assert_contains "$(cat "$block_output")" "payload" "BLPOP"

pubsub_output="$WORK_DIR/pubsub.out"
cli_at "$MAIN_PORT" subscribe harmony.channel >"$pubsub_output" &
pubsub_pid=$!
sleep 0.3
assert_eq "1" "$(cli_at "$MAIN_PORT" publish harmony.channel message)" "PUBLISH"
attempt=0
while [ "$attempt" -lt 50 ] && ! grep -q message "$pubsub_output" 2>/dev/null; do
    attempt=$((attempt + 1))
    sleep 0.1
done
assert_contains "$(cat "$pubsub_output")" "message" "SUBSCRIBE"
kill "$pubsub_pid" >/dev/null 2>&1 || true
wait "$pubsub_pid" >/dev/null 2>&1 || true

# CONFIG SET takes name/value pairs. This MULTI_ARG_CONFIG value must remain
# one bulk string; Redis splits it into class/hard/soft/seconds internally.
pubsub_limit="pubsub 64kb 64kb 1"
original_pubsub_limit=$(cli_at "$MAIN_PORT" config get client-output-buffer-limit | tail -n 1)
assert_eq "OK" "$(cli_at "$MAIN_PORT" config set client-output-buffer-limit "$pubsub_limit")" "set pubsub output buffer limit"
coproc SLOW_SUBSCRIBER { cli_at "$MAIN_PORT" subscribe harmony.slow-channel; }
slow_subscriber_pid=$SLOW_SUBSCRIBER_PID
attempt=0
slow_client=""
while [ "$attempt" -lt 50 ]; do
    slow_client=$(cli_at "$MAIN_PORT" client list type pubsub 2>/dev/null || true)
    [ -n "$slow_client" ] && break
    attempt=$((attempt + 1))
    sleep 0.1
done
assert_contains "$slow_client" "flags=P" "slow pubsub client connected"
large_message=$(head -c 16384 /dev/zero | tr '\0' x)
publish_count=0
while [ "$publish_count" -lt 512 ]; do
    slow_client=$(cli_at "$MAIN_PORT" client list type pubsub 2>/dev/null || true)
    [ -z "$slow_client" ] && break
    cli_at "$MAIN_PORT" publish harmony.slow-channel "$large_message" >/dev/null
    publish_count=$((publish_count + 1))
done
attempt=0
while [ "$attempt" -lt 100 ]; do
    slow_client=$(cli_at "$MAIN_PORT" client list type pubsub 2>/dev/null || true)
    [ -z "$slow_client" ] && break
    attempt=$((attempt + 1))
    sleep 0.1
done
assert_eq "" "$slow_client" "pubsub output buffer hard-limit eviction"
kill "$slow_subscriber_pid" >/dev/null 2>&1 || true
wait "$slow_subscriber_pid" >/dev/null 2>&1 || true
assert_eq "OK" "$(cli_at "$MAIN_PORT" config set client-output-buffer-limit "$original_pubsub_limit")" "restore pubsub output buffer limit"

rdb_dir="$WORK_DIR/rdb"
start_server "$RDB_PORT" "$rdb_dir"
assert_eq "OK" "$(cli_at "$RDB_PORT" set harmony:rdb persisted)" "RDB SET"
assert_eq "OK" "$(cli_at "$RDB_PORT" save)" "SAVE"
assert_file "$rdb_dir/dump.rdb" "RDB output"
$REDIS_CHECK_RDB "$rdb_dir/dump.rdb" >/dev/null
ASSERTIONS=$((ASSERTIONS + 1))
dd if="$rdb_dir/dump.rdb" of="$rdb_dir/corrupt.rdb" bs=1 count=16 >/dev/null 2>&1
if $REDIS_CHECK_RDB "$rdb_dir/corrupt.rdb" >/dev/null 2>&1; then
    fail "redis-check-rdb accepted a truncated RDB"
fi
ASSERTIONS=$((ASSERTIONS + 1))
stop_server "$RDB_PORT"
start_server "$RDB_PORT" "$rdb_dir"
assert_eq "persisted" "$(cli_at "$RDB_PORT" get harmony:rdb)" "RDB restart recovery"

if $REDIS_SERVER --port not-a-port >"$WORK_DIR/invalid-config.log" 2>&1; then
    fail "redis-server accepted an invalid port"
fi
ASSERTIONS=$((ASSERTIONS + 1))

AOF_DIR="$WORK_DIR/aof"
start_server "$AOF_PORT" "$AOF_DIR" --appendonly yes --appenddirname appendonlydir
assert_eq "OK" "$(cli_at "$AOF_PORT" set harmony:aof persisted)" "AOF SET"
assert_eq "1" "$(cli_at "$AOF_PORT" lpush harmony:aof-list item)" "AOF LPUSH"
assert_eq "Background append only file rewriting started" "$(cli_at "$AOF_PORT" bgrewriteaof)" "BGREWRITEAOF"
wait_info_value "$AOF_PORT" persistence aof_rewrite_in_progress 0 || fail "AOF rewrite timed out"
assert_eq "ok" "$(cli_at "$AOF_PORT" info persistence | tr -d '\r' | sed -n 's/^aof_last_bgrewrite_status://p')" "AOF rewrite status"
stop_server "$AOF_PORT"
aof_files=$(find "$AOF_DIR/appendonlydir" -type f -name '*.aof' -print 2>/dev/null || true)
[ -n "$aof_files" ] || fail "no AOF data file produced"
for aof_file in $aof_files; do
    $REDIS_CHECK_AOF "$aof_file" >/dev/null
    ASSERTIONS=$((ASSERTIONS + 1))
done
first_aof=$(printf '%s\n' $aof_files | sed -n '1p')
cp "$first_aof" "$AOF_DIR/corrupt.aof"
printf 'not-resp-data\n' >>"$AOF_DIR/corrupt.aof"
if $REDIS_CHECK_AOF "$AOF_DIR/corrupt.aof" >/dev/null 2>&1; then
    fail "redis-check-aof accepted corrupted AOF data"
fi
ASSERTIONS=$((ASSERTIONS + 1))
start_server "$AOF_PORT" "$AOF_DIR" --appendonly yes --appenddirname appendonlydir
assert_eq "persisted" "$(cli_at "$AOF_PORT" get harmony:aof)" "AOF restart recovery"
assert_eq "item" "$(cli_at "$AOF_PORT" lindex harmony:aof-list 0)" "AOF list recovery"

master_dir="$WORK_DIR/master"
replica_dir="$WORK_DIR/replica"
start_server "$MASTER_PORT" "$master_dir"
start_server "$REPLICA_PORT" "$replica_dir" --replicaof 127.0.0.1 "$MASTER_PORT"
wait_info_value "$REPLICA_PORT" replication master_link_status up || fail "replica link did not become ready"
assert_eq "OK" "$(cli_at "$MASTER_PORT" set harmony:replication copied)" "replication SET"
attempt=0
replicated=""
while [ "$attempt" -lt 100 ]; do
    replicated=$(cli_at "$REPLICA_PORT" get harmony:replication 2>/dev/null || true)
    [ "$replicated" = "copied" ] && break
    attempt=$((attempt + 1))
    sleep 0.1
done
assert_eq "copied" "$replicated" "replica read"
assert_eq "1" "$(cli_at "$MASTER_PORT" wait 1 5000)" "WAIT replica acknowledgement"
waitaof_result=$(cli_at "$MASTER_PORT" waitaof 0 1 5000 | tr '\n' ':')
assert_eq "0:1:" "$waitaof_result" "WAITAOF replica acknowledgement"

assert_eq "OK" "$(cli_at "$MASTER_PORT" failover to 127.0.0.1 "$REPLICA_PORT" timeout 10000)" "FAILOVER to explicit replica"
wait_info_value "$REPLICA_PORT" replication role master || fail "replica was not promoted by FAILOVER"
wait_info_value "$MASTER_PORT" replication role slave || fail "master was not demoted by FAILOVER"
assert_eq "master" "$(cli_at "$REPLICA_PORT" info replication | tr -d '\r' | sed -n 's/^role://p')" "FAILOVER promoted role"
assert_eq "slave" "$(cli_at "$MASTER_PORT" info replication | tr -d '\r' | sed -n 's/^role://p')" "FAILOVER demoted role"
assert_eq "OK" "$(cli_at "$REPLICA_PORT" set harmony:failover promoted)" "write after FAILOVER"
assert_eq "promoted" "$(cli_at "$MASTER_PORT" get harmony:failover)" "replication after FAILOVER"

assert_eq "OK" "$(cli_at "$REPLICA_PORT" failover to 127.0.0.1 "$MASTER_PORT" timeout 10000)" "FAILOVER restore original master"
wait_info_value "$MASTER_PORT" replication role master || fail "original master was not restored"
wait_info_value "$REPLICA_PORT" replication role slave || fail "original replica was not restored"
assert_eq "master" "$(cli_at "$MASTER_PORT" info replication | tr -d '\r' | sed -n 's/^role://p')" "restored master role"
assert_eq "slave" "$(cli_at "$REPLICA_PORT" info replication | tr -d '\r' | sed -n 's/^role://p')" "restored replica role"

stop_server "$REPLICA_PORT"
wait_info_value "$MASTER_PORT" replication connected_slaves 0 || fail "stopped replica remained connected"
assert_eq "OK" "$(cli_at "$MASTER_PORT" set harmony:wait-timeout value)" "write with replica offline"
assert_eq "0" "$(cli_at "$MASTER_PORT" wait 1 200)" "WAIT timeout with replica offline"
waitaof_result=$(cli_at "$MASTER_PORT" waitaof 0 1 200 | tr '\n' ':')
assert_eq "0:0:" "$waitaof_result" "WAITAOF timeout with replica offline"
assert_eq "OK" "$(cli_at "$MASTER_PORT" config set min-replicas-to-write 1)" "enable minimum replica write guard"
assert_eq "OK" "$(cli_at "$MASTER_PORT" config set min-replicas-max-lag 1)" "set minimum replica lag"
no_replicas=$(cli_at "$MASTER_PORT" set harmony:guard rejected 2>&1 || true)
assert_contains "$no_replicas" "NOREPLICAS" "minimum replica write rejection"
assert_eq "OK" "$(cli_at "$MASTER_PORT" config set min-replicas-to-write 0)" "disable minimum replica write guard"
start_server "$REPLICA_PORT" "$replica_dir" --replicaof 127.0.0.1 "$MASTER_PORT"
wait_info_value "$REPLICA_PORT" replication master_link_status up || fail "restarted replica link did not become ready"
assert_eq "value" "$(cli_at "$REPLICA_PORT" get harmony:wait-timeout)" "replica recovery after restart"

sentinel_dir="$WORK_DIR/sentinel"
mkdir -p "$sentinel_dir"
sentinel_conf="$sentinel_dir/sentinel.conf"
cat >"$sentinel_conf" <<EOF
bind 127.0.0.1
protected-mode no
port $SENTINEL_PORT
daemonize yes
pidfile $sentinel_dir/redis.pid
logfile $sentinel_dir/redis.log
dir $sentinel_dir
sentinel monitor harmony-master 127.0.0.1 $MASTER_PORT 1
sentinel down-after-milliseconds harmony-master 500
sentinel failover-timeout harmony-master 5000
EOF
$REDIS_SENTINEL "$sentinel_conf"
PORTS="$PORTS $SENTINEL_PORT"
wait_ready "$SENTINEL_PORT" || fail "redis-sentinel did not become ready"
master_address=$(cli_at "$SENTINEL_PORT" sentinel get-master-addr-by-name harmony-master)
assert_contains "$master_address" "127.0.0.1" "Sentinel master host"
assert_contains "$master_address" "$MASTER_PORT" "Sentinel master port"
assert_eq "1" "$(cli_at "$SENTINEL_PORT" sentinel ckquorum harmony-master | sed -n 's/^OK .*/1/p')" "Sentinel quorum"

cluster_ports="$CLUSTER_1_PORT $CLUSTER_2_PORT $CLUSTER_3_PORT"
for port in $cluster_ports; do
    cluster_dir="$WORK_DIR/cluster-$port"
    start_server "$port" "$cluster_dir" \
        --cluster-enabled yes \
        --cluster-config-file "nodes-$port.conf" \
        --cluster-node-timeout 5000 \
        --cluster-announce-ip 127.0.0.1 \
        --cluster-announce-port "$port" \
        --cluster-announce-bus-port "$((port + 10000))"
done
$REDIS_CLI --cluster create \
    "127.0.0.1:$CLUSTER_1_PORT" \
    "127.0.0.1:$CLUSTER_2_PORT" \
    "127.0.0.1:$CLUSTER_3_PORT" \
    --cluster-replicas 0 --cluster-yes >"$WORK_DIR/cluster-create.log"
for port in $cluster_ports; do
    wait_cluster_state "$port" ok || fail "cluster node $port did not become ready"
    cluster_state=$(cli_at "$port" cluster info | tr -d '\r' | sed -n 's/^cluster_state://p')
    assert_eq "ok" "$cluster_state" "Cluster state on node $port"
done
assert_eq "OK" "$($REDIS_CLI -h 127.0.0.1 -p "$CLUSTER_1_PORT" -c --raw set '{harmony}:cluster' value)" "Cluster SET"
assert_eq "value" "$($REDIS_CLI -h 127.0.0.1 -p "$CLUSTER_2_PORT" -c --raw get '{harmony}:cluster')" "Cluster redirected GET"

benchmark_output=$($REDIS_BENCHMARK -h 127.0.0.1 -p "$MAIN_PORT" -n 20000 -c 16 -P 4 -t set,get -q)
assert_contains "$benchmark_output" "SET:" "redis-benchmark SET"
assert_contains "$benchmark_output" "GET:" "redis-benchmark GET"

assert_eq "1" "$(cli_at "$MAIN_PORT" del harmony:string)" "DEL"

stop_server "$CLUSTER_3_PORT"
for port in $CLUSTER_1_PORT $CLUSTER_2_PORT; do
    wait_cluster_state "$port" fail || fail "cluster node $port did not detect the outage"
    cluster_state=$(cli_at "$port" cluster info | tr -d '\r' | sed -n 's/^cluster_state://p')
    assert_eq "fail" "$cluster_state" "Cluster state after node exit on node $port"
done
cluster_down=$($REDIS_CLI -h 127.0.0.1 -p "$CLUSTER_1_PORT" -c --raw get '{harmony}:cluster' 2>&1 || true)
assert_contains "$cluster_down" "CLUSTERDOWN" "Cluster rejects commands without full coverage"
cluster_3_dir="$WORK_DIR/cluster-$CLUSTER_3_PORT"
start_server "$CLUSTER_3_PORT" "$cluster_3_dir" \
    --cluster-enabled yes \
    --cluster-config-file "nodes-$CLUSTER_3_PORT.conf" \
    --cluster-node-timeout 5000 \
    --cluster-announce-ip 127.0.0.1 \
    --cluster-announce-port "$CLUSTER_3_PORT" \
    --cluster-announce-bus-port "$((CLUSTER_3_PORT + 10000))"
for port in $cluster_ports; do
    wait_cluster_state "$port" ok || fail "cluster node $port did not recover"
    cluster_state=$(cli_at "$port" cluster info | tr -d '\r' | sed -n 's/^cluster_state://p')
    assert_eq "ok" "$cluster_state" "Cluster recovery on node $port"
done
assert_eq "3" "$(cli_at "$CLUSTER_1_PORT" cluster info | tr -d '\r' | sed -n 's/^cluster_known_nodes://p')" "Cluster node count after recovery"

stop_server "$MASTER_PORT"
attempt=0
sentinel_master_port=""
while [ "$attempt" -lt 300 ]; do
    sentinel_master_port=$(cli_at "$SENTINEL_PORT" sentinel get-master-addr-by-name harmony-master 2>/dev/null | tail -n 1 || true)
    [ "$sentinel_master_port" = "$REPLICA_PORT" ] && break
    attempt=$((attempt + 1))
    sleep 0.1
done
assert_eq "$REPLICA_PORT" "$sentinel_master_port" "Sentinel promotes replica after master exit"
wait_info_value "$REPLICA_PORT" replication role master || fail "Sentinel-promoted replica did not become master"
assert_eq "master" "$(cli_at "$REPLICA_PORT" info replication | tr -d '\r' | sed -n 's/^role://p')" "Sentinel promoted role"
assert_eq "OK" "$(cli_at "$REPLICA_PORT" set harmony:sentinel promoted)" "write on Sentinel-promoted master"
start_server "$MASTER_PORT" "$master_dir" --replicaof 127.0.0.1 "$REPLICA_PORT"
wait_info_value "$MASTER_PORT" replication master_link_status up || fail "restarted old master did not become a replica"
assert_eq "slave" "$(cli_at "$MASTER_PORT" info replication | tr -d '\r' | sed -n 's/^role://p')" "old master rejoins as replica"
assert_eq "promoted" "$(cli_at "$MASTER_PORT" get harmony:sentinel)" "Sentinel failover replication continuity"

echo "redis 8.2.7 extended package test passed: $ASSERTIONS assertions"
