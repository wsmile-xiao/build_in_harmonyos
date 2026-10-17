#!/usr/bin/env bash
# test_mpd.sh — mpd 0.24.12 消费者测试 C1-C4（R40 实质验证）
# Usage: test_mpd.sh <mpd-package-dir>
#
# 真实断言：每个检查不满足即非零退出；无硬编码通过。
# 由 test_package/conanfile.py 显式经 bash 调用（脚本使用 pipefail 与
# /dev/tcp，非 POSIX sh）。
# MPD 0.24 配置格式为 name "value"（无 = 号，新解析器 Tokenizer）；
# 配置文件路径为位置参数（0.24 主程序无 --config 选项）。
set -euo pipefail

PKG="$1"
MPD="$PKG/bin/mpd"
RUN_DECODER="$PKG/bin/run_decoder"
fail=0

# OHOS /tmp 只读（E002）：优先 $TMPDIR，回退 $HOME/tmp
tmpbase="${TMPDIR:-$HOME/tmp}"
mkdir -p "$tmpbase" || { echo "FAIL: cannot create temp base $tmpbase"; exit 1; }
work=$(mktemp -d "$tmpbase/mpd-test.XXXXXX")
# EXIT trap 必须保留脚本原始退出码：set -e 下 trap 内 kill/wait 空 mpd_pid
# 非零会 abort 并覆盖成功状态（C2 已 kill+wait 后置 mpd_pid=""）。
cleanup() {
    rc=$?
    if [ -n "${mpd_pid:-}" ]; then
        kill "$mpd_pid" 2>/dev/null || true
        wait "$mpd_pid" 2>/dev/null || true
    fi
    rm -rf "${work:-}" 2>/dev/null || true
    exit "$rc"
}
trap cleanup EXIT
mpd_pid=""

# --- C1: 版本信息 ---
echo "== C1: mpd --version =="
if [ ! -x "$MPD" ]; then
    echo "FAIL: mpd binary missing or not executable: $MPD"
    exit 1
fi
out=$("$MPD" --version)
echo "$out" | head -3
case "$out" in
    *"0.24.12"*) echo "ok   : C1 version 0.24.12" ;;
    *) echo "FAIL: C1 version is not 0.24.12"; fail=$((fail + 1)) ;;
esac

# --- 生成测试音频（440Hz 0.5s 单声道 16bit wav） ---
python3 - "$work/sample.wav" <<'EOF'
import wave, math, struct, sys
w = wave.open(sys.argv[1], 'wb')
w.setnchannels(1)
w.setsampwidth(2)
w.setframerate(44100)
w.writeframes(b''.join(struct.pack('<h', int(8000 * math.sin(2 * math.pi * 440 * i / 44100)))
                       for i in range(22050)))
w.close()
EOF
echo "ok   : sample.wav generated ($(wc -c < "$work/sample.wav") bytes)"

# --- C2: 配置解析 + 启动 + HTTP 监听 + 曲库导入 ---
echo "== C2: daemon start + library import =="
mkdir -p "$work/music"
cp "$work/sample.wav" "$work/music/sample.wav"
cat > "$work/mpd.conf" <<EOF
music_directory "$work/music"
db_file "$work/db"
log_file "$work/log"
log_level "info"
pid_file "$work/pid"
bind_to_address "127.0.0.1"
port "6601"
EOF
"$MPD" --no-daemon "$work/mpd.conf" > "$work/run.out" 2>&1 &
mpd_pid=$!
sleep 5
if ! kill -0 "$mpd_pid" 2>/dev/null; then
    echo "FAIL: C2 mpd exited early:"
    head -5 "$work/run.out" || true
    fail=$((fail + 1))
else
    echo "ok   : C2 mpd running (pid=$mpd_pid)"
    # MPD 0.24 绑定成功无日志（Listen.cxx 仅失败时抛 "Failed to listen on"），
    # 故以直接连接 MPD 协议端口读 greeting 作为"实际监听"的证明。
    # 注意：协议 banner 版本为 0.24.0（上游 GitVersion 烘焙值），与
    # --version 的 0.24.12 不同 —— 仅断言 "OK MPD" 前缀，不断言版本号。
    greeting=$(bash -c 'read -t 3 -r line < /dev/tcp/127.0.0.1/6601 && printf "%s" "$line"' 2>/dev/null) || true
    case "$greeting" in
        "OK MPD"*) echo "ok   : C2 MPD protocol handshake: $greeting" ;;
        *) echo "FAIL: C2 MPD protocol handshake failed (greeting='$greeting'):"
           tail -5 "$work/log" 2>/dev/null || true
           fail=$((fail + 1)) ;;
    esac
    if grep -q "added" "$work/log" 2>/dev/null && grep -q "sample.wav" "$work/log" 2>/dev/null; then
        echo "ok   : C2 library import (scan added sample.wav)"
    else
        echo "FAIL: C2 library import not found in log:"
        tail -5 "$work/log" 2>/dev/null || true
        fail=$((fail + 1))
    fi
    kill "$mpd_pid" 2>/dev/null || true
    wait "$mpd_pid" 2>/dev/null || true
    mpd_pid=""
fi

# --- C3: 解码后端初始化（run_decoder 经 ffmpeg 后端解码 wav） ---
echo "== C3: decoder backend (run_decoder ffmpeg wav) =="
if [ ! -x "$RUN_DECODER" ]; then
    echo "FAIL: C3 run_decoder missing in package: $RUN_DECODER"
    fail=$((fail + 1))
else
    if "$RUN_DECODER" ffmpeg "$work/sample.wav" > "$work/dec.out" 2>&1; then
        head -2 "$work/dec.out"
        if head -1 "$work/dec.out" | grep -q "audio_format="; then
            echo "ok   : C3 decoder backend initialized (audio_format reported)"
        else
            echo "FAIL: C3 no audio_format in decoder output"
            fail=$((fail + 1))
        fi
    else
        echo "FAIL: C3 run_decoder exited non-zero:"
        head -5 "$work/dec.out" || true
        fail=$((fail + 1))
    fi
fi

# --- C4: 播放闭环（null 输出 + 协议播放状态机，R40 核心功能验证） ---
# null 输出后端无条件编译（src/output/plugins/meson.build 初始值），零新依赖、
# 无音频设备需求：协议 → 队列 → 解码 → 输出线程 → 播毕 全链路端到端。
echo "== C4: end-to-end playback (null output) =="
# 3s wav（稳定状态窗口捕获；0.5s 过短无法稳定捕获 play 状态）
python3 - "$work/sample_c4.wav" <<'EOF'
import wave, math, struct, sys
w = wave.open(sys.argv[1], 'wb')
w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100)
w.writeframes(b''.join(struct.pack('<h', int(8000 * math.sin(2 * math.pi * 440 * i / 44100)))
                       for i in range(132300)))
w.close()
EOF
mkdir -p "$work/music4"
cp "$work/sample_c4.wav" "$work/music4/"
cat > "$work/mpd4.conf" <<EOF
music_directory "$work/music4"
db_file "$work/db4"
log_file "$work/log4"
log_level "info"
pid_file "$work/pid4"
bind_to_address "127.0.0.1"
port "6602"
audio_output {
type "null"
name "NullOut"
}
EOF
"$MPD" --no-daemon "$work/mpd4.conf" > "$work/run4.out" 2>&1 &
mpd_pid=$!
sleep 5
if ! kill -0 "$mpd_pid" 2>/dev/null; then
    echo "FAIL: C4 mpd exited early:"
    head -5 "$work/run4.out" || true
    fail=$((fail + 1))
else
    echo "ok   : C4 mpd running (pid=$mpd_pid, null output)"
    # 协议顺序（实测坑）：play N 是播放列表索引（空列表报 Bad song index）；
    # add <uri> 用 music_directory 相对路径（0: 前缀报 No such directory）。
    if python3 - <<'PYEOF'
import socket, time, sys

def read_reply(s, cmd=None):
    # MPD 协议应答以 OK/ACK/ERROR 行终止；单次 recv 可能只拿到部分字段，
    # 必须读到终止行为止（修检视 P2：partial-read 竞态致 state 偶发漏采）。
    if cmd is not None:
        s.sendall(cmd)
    buf = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
        text = buf.decode(errors="replace")
        for line in reversed(text.splitlines()):
            line = line.strip()
            if not line:
                continue
            if line.startswith(("OK", "ACK", "ERROR")):
                return text
            break
    return text

saw_play = False
saw_stop = False
try:
    s = socket.create_connection(("127.0.0.1", 6602), timeout=5)
    s.settimeout(5)
    read_reply(s)                        # greeting
    read_reply(s, b"listall\n")
    add_reply = read_reply(s, b"add sample_c4.wav\n")
    # 修检视 P3：add 失败返回 ERROR（本版本成功返回 OK，0.24.12 实测），
    # 出现 ERROR 即判负并给出真实原因，避免落入 play 0 的 "Bad song index"
    # （空列表）误导；不强制 ACK 前缀——MPD 各版本 add 应答 OK/ACK 不一，
    # ERROR 为唯一失败信号（跨版本兼容）
    if "ERROR" in add_reply:
        print("C4_ERR: add sample_c4.wav rejected:", add_reply.strip())
        sys.exit(1)
    read_reply(s, b"play 0\n")
    # 状态机轮询：3s 曲目，play 窗口约 0.5-3.5s；0.3s × 40（12s 窗口）留足余量
    for _ in range(40):
        time.sleep(0.3)
        reply = read_reply(s, b"status\n")
        lines = dict(l.split(": ", 1) for l in reply.splitlines() if ": " in l)
        st = lines.get("state")
        if st == "play":
            saw_play = True
        if st == "stop" and saw_play:
            saw_stop = True
            break
    s.sendall(b"quit\n")
except Exception as e:
    print("C4_ERR:", repr(e)); sys.exit(1)
sys.exit(0 if (saw_play and saw_stop) else 1)
PYEOF
    then
        echo "ok   : C4 playback end-to-end (play -> stop state machine observed)"
    else
        echo "FAIL: C4 playback state machine not observed (play -> stop):"
        tail -5 "$work/log4" 2>/dev/null || true
        fail=$((fail + 1))
    fi
    kill "$mpd_pid" 2>/dev/null || true
    wait "$mpd_pid" 2>/dev/null || true
    mpd_pid=""
fi

echo "== summary: fail=$fail =="
if [ "$fail" -ne 0 ]; then
    exit 1
fi
echo "PASS: all C1-C4 checks passed"
