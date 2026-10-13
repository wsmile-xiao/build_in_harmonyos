#!/bin/sh
# 真机端到端回环：ss-server + ss-local + 内建 HTTP 源站，SOCKS5 隧道逐字节校验
set -u
# 取绝对路径（P2-5）：原写法 D 为相对路径，若调用方 CWD 与脚本目录
# 不同，$D 传给测试作 bindir 后会被二次解析而找不到 ss-server/ss-local。
D=$(cd "$(dirname "$0")" && pwd) || { echo "ERROR: 无法解析脚本目录"; exit 1; }
cd "$D" || { echo "ERROR: 无法进入目录 $D"; exit 1; }

# 设备侧 PATH/LD_LIBRARY_PATH：payload 目录内含 ss-* 与 libev.so
export LD_LIBRARY_PATH="$D${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PATH="$D:$PATH"

# 显式检查二进制存在，区分"缺文件"与"测试失败"（不再被 2>/dev/null 吞掉）
for f in ss-local ss-server test_shadowsocks_e2e libev.so; do
    if [ ! -f "$f" ]; then
        echo "ERROR: payload 缺少 $f"
        echo "__RC__=2"
        exit 2
    fi
done
chmod +x ss-local ss-server test_shadowsocks_e2e || {
    echo "ERROR: chmod 失败"; echo "__RC__=2"; exit 2; }

echo "=== env ==="
uname -a
echo "=== libs ==="
ls -la libev.so ss-local ss-server test_shadowsocks_e2e
echo "=== run consumer e2e ==="
./test_shadowsocks_e2e "$D"
rc=$?
echo "__RC__=$rc"
exit $rc
