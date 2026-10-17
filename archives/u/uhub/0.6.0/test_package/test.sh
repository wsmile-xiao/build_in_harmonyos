#!/bin/bash
# uhub 0.6.0 L1 测试：真实执行包内可执行文件（版本 / 用户库 / 配置解析 / 服务启动与插件加载）
set -euo pipefail

: "${UHUB_BIN:?UHUB_BIN is required}"
: "${UHUB_PASSWD_BIN:?UHUB_PASSWD_BIN is required}"
: "${UHUB_PLUGIN_DIR:?UHUB_PLUGIN_DIR is required}"

echo "== 1) 版本信息 =="
"$UHUB_BIN" -V

echo "== 2) uhub-passwd 用户库增删查（sqlite3 链接） =="
DB="$PWD/users.db"
rm -f "$DB"
"$UHUB_PASSWD_BIN" "$DB" create
"$UHUB_PASSWD_BIN" "$DB" add conan testers
"$UHUB_PASSWD_BIN" "$DB" list

echo "== 3) 插件产物 =="
test -f "$UHUB_PLUGIN_DIR/mod_welcome.so"
ls -1 "$UHUB_PLUGIN_DIR"

echo "== 4) 配置解析（uhub -C，file_plugins 指向包内插件） =="
cat > acl.conf <<EOF
deny_nick Administrator
EOF
cat > plugins-test.conf <<EOF
plugin $UHUB_PLUGIN_DIR/mod_welcome.so
EOF
cat > uhub-test.conf <<EOF
server_port=31511
hub_name=conan test hub
max_users=10
file_acl=$PWD/acl.conf
file_plugins=$PWD/plugins-test.conf
EOF
"$UHUB_BIN" -C -c uhub-test.conf

echo "== 5) 真实启动：监听端口 + 加载插件 =="
"$UHUB_BIN" -c uhub-test.conf -p "$PWD/uhub.pid" > hub.log 2>&1 &
HUB_PID=$!
sleep 3
cat hub.log
grep -q "listening" hub.log
grep -q "Loaded plugin" hub.log
kill "$HUB_PID" 2>/dev/null || true   # 进程可能已自然退出，忽略 kill 失败
wait "$HUB_PID" 2>/dev/null || true   # 同上：仅回收子进程，无失败语义
echo "ALL OK"
