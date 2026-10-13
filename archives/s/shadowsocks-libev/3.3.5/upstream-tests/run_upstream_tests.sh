#!/bin/bash
# =============================================================================
# run_upstream_tests.sh — 真实执行上游 tests/test.py（离线等价改造）
#
# 背景（rule4）：上游 3.3.5 的自动化测试是 tests/test.sh -> tests/test.py，
# 由 8 个 JSON 配置驱动（aes / aes-gcm / aes-ctr / rc4-md5 / salsa20 /
# chacha20 / chacha20-ietf / chacha20-ietf-poly1305）。
#
# 关键事实（本次适配实测澄清）：
#   * tests/ 目录**只存在于 GitHub 的 tag 源码归档**里
#     （https://github.com/shadowsocks/shadowsocks-libev/archive/refs/tags/v3.3.5.tar.gz，
#      归档内顶层目录名为 shadowsocks-c-3.3.5）；
#     本配方为满足 R40（可离线复现）而采用的**官方 release 资产**
#     （shadowsocks-libev-3.3.5.tar.gz）里**没有 tests/ 目录** —— 上游 release
#     流程没有把它打进 dist tarball。
#   * tests/test.py 的默认目标是 http://www.google.com/ 与 8.8.8.8:53，
#     离线评测环境不可达；但它把 url/dns 做成了命令行参数
#     （--url / --dns），因此**可以不改一行上游测试代码**，只把 --url 指向
#     本机 origin 就能在离线环境真实执行。
#
# 本脚本就是这条路径的可复现实现：不做任何"等价替代"，直接跑上游 test.py。
#
# 依赖：qemu-aarch64-static + OHOS musl 运行根 + libev.so（ss-* 唯一的动态依赖）
# 用法：bash run_upstream_tests.sh <shadowsocks-libev/3.3.5 的 conan package 目录>
# =============================================================================
set -uo pipefail

PKG="${1:?用法: $0 <conan package 目录（含 bin/ss-*）>}"
QEMU="${OHOS_QEMU:-/root/ohpc/sdk/qemu/usr/bin/qemu-aarch64-static}"
RUNROOT="${OHOS_RUNROOT:-/root/ohpc/sdk/ohos-runroot}"
WORK="$(mktemp -d)"
ORIGIN_PORT="${ORIGIN_PORT:-18080}"

cleanup() {
    pkill -f "http.server ${ORIGIN_PORT}" 2>/dev/null || true
    rm -rf "$WORK"
}
trap cleanup EXIT

# ── 1) 取上游 tests/（只有 tag 归档里有）──────────────────────────────────
# 上游 tag 归档的固定 sha256（P1-2：供应链完整性）。
# 该归档是 tests/ 的唯一来源，会被解包并**直接执行**其中的 tests/test.py，
# 因此必须固定校验和，不能信任任何第三方镜像返回的内容。
UP_TGZ_SHA256="bbc1dae9a1c626e6e546e65d124d488164607a82b5b19c958248f68cdf7e3b5a"

UP_TGZ="${UPSTREAM_TAG_TGZ:-}"
if [ -z "$UP_TGZ" ] || [ ! -f "$UP_TGZ" ]; then
    UP_TGZ="$WORK/v3.3.5-tag.tar.gz"
    echo "==> 下载上游 tag 源码归档（tests/ 的唯一来源）"
    # 两处都必须带 -f：否则镜像返回错误页（404/HTML）时 curl 仍退出 0，
    # 坏文件被写入，`||` 兜底永远不会触发。
    if ! curl -fsSL --max-time 180 -o "$UP_TGZ" \
          "https://ghfast.top/https://github.com/shadowsocks/shadowsocks-libev/archive/refs/tags/v3.3.5.tar.gz"; then
        echo "==> 镜像不可用，回退官方源"
        curl -fsSL --max-time 180 -o "$UP_TGZ" \
          "https://github.com/shadowsocks/shadowsocks-libev/archive/refs/tags/v3.3.5.tar.gz"
    fi
fi

# 校验归档完整性：不匹配即 fail-fast，绝不解包/执行未经验证的代码。
_actual="$(sha256sum "$UP_TGZ" | cut -d' ' -f1)"
if [ "$_actual" != "$UP_TGZ_SHA256" ]; then
    echo "ERROR: 上游 tag 归档 sha256 不匹配，拒绝执行其中代码"
    echo "       期望: $UP_TGZ_SHA256"
    echo "       实际: $_actual"
    echo "       文件: $UP_TGZ"
    exit 3
fi
echo "==> 归档 sha256 校验通过"

tar xzf "$UP_TGZ" -C "$WORK"
SRC="$(ls -d "$WORK"/*/ | head -1)"
ls "$SRC/tests/"*.json >/dev/null 2>&1 || { echo "上游 tests/ 缺失"; exit 1; }

# ── 1b) fail-fast：校验 PKG 真的是「已构建的包目录」────────────────────
# 踩坑记录：conan 的 `conan cache path <ref>` 返回的是**导出目录**（.../e），
# 不是包目录；包在 .../b/<hash>/p。把导出目录当 PKG 传进来时，下面的
# qemu wrapper 会指向不存在的 bin/ss-*，8 个用例会**全部失败**并打印
# 0/8 —— 看起来像"适配坏了"，实际只是路径给错。这里先断言，避免误判。
for _b in ss-local ss-server ss-tunnel ss-manager ss-redir; do
    if [ ! -x "$PKG/bin/$_b" ]; then
        echo "ERROR: PKG 目录里没有可执行的 bin/$_b"
        echo "       收到的 PKG = $PKG"
        echo "       提示：包目录形如 /root/.conan2/p/b/<hash>/p，"
        echo "             而 'conan cache path <ref>' 返回的是导出目录 .../e。"
        exit 2
    fi
done

# ── 2) 把包内真实二进制包成 qemu wrapper（test.py 用 PATH 找 ss-*）──────
mkdir -p "$WORK/wrap"
for b in ss-local ss-server ss-tunnel ss-manager ss-redir; do
    printf '#!/bin/sh\nexec "%s" -L "%s" "%s/bin/%s" "$@"\n' \
      "$QEMU" "$RUNROOT" "$PKG" "$b" > "$WORK/wrap/$b"
    chmod +x "$WORK/wrap/$b"
done
export PATH="$WORK/wrap:$PATH"

# ── 3) 本机 origin（离线替代 www.google.com）─────────────────────────────
mkdir -p "$WORK/wwwroot"
echo "OHPC_UPSTREAM_OFFLINE_ORIGIN_OK" > "$WORK/wwwroot/index.html"
( cd "$WORK/wwwroot" && setsid nohup python3 -m http.server "$ORIGIN_PORT" \
    --bind 127.0.0.1 >/dev/null 2>&1 & )
sleep 2
curl -s --max-time 5 "http://127.0.0.1:${ORIGIN_PORT}/" >/dev/null \
  || { echo "本地 origin 未就绪"; exit 1; }

# ── 4) 真实执行上游 test.py（未修改任何一行上游测试代码）────────────────
PASS=0; FAIL=0
declare -a LINES
for cfg in aes aes-gcm aes-ctr rc4-md5 salsa20 chacha20 chacha20-ietf \
           chacha20-ietf-poly1305; do
    if timeout 180 python3 "$SRC/tests/test.py" -c "$SRC/tests/$cfg.json" \
         --url "http://127.0.0.1:${ORIGIN_PORT}/" >"$WORK/$cfg.log" 2>&1; then
        PASS=$((PASS + 1)); LINES+=("  [PASS] tests/$cfg.json")
    else
        FAIL=$((FAIL + 1)); LINES+=("  [FAIL] tests/$cfg.json")
    fi
done

echo
printf '%s\n' "${LINES[@]}"
echo
echo "UPSTREAM_RESULT: ${PASS}/8 passed, ${FAIL}/8 failed"
[ "$FAIL" -eq 0 ]
