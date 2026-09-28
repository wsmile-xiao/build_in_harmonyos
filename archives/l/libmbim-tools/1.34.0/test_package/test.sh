#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer tests for the libmbim-tools executables.
#
# Runs inside the conanrun environment: the package bin/ is on PATH and the
# glib shared libraries are on LD_LIBRARY_PATH.  Every tool is actually
# executed and its real output is asserted (R34: no print-only shell test).
#
# Device-free by design: the CI worker has no MBIM modem, so the complete
# consumer case drives mbimcli's full MBIM message-decode pipeline
#   hex string -> MbimMessage -> mbim_message_validate -> structured printable
# via `--printable`, which runs before the device check and therefore needs no
# hardware.  This is the tool's core end-to-end functionality.
set -eu

VERSION="1.34.0"

check_version() {
    tool="$1"
    echo "----- ${tool} --version -----"
    out="$("${tool}" --version)"
    echo "${out}"
    case "${out}" in
        *"${tool} ${VERSION}"*) echo "OK: ${tool} reports ${VERSION}" ;;
        *) echo "FAIL: ${tool} did not report expected version ${VERSION}" >&2; exit 1 ;;
    esac
}

check_help() {
    tool="$1"
    echo "----- ${tool} --help -----"
    "${tool}" --help > /dev/null
    echo "OK: ${tool} --help"
}

# ── Smoke: version banners (mbimcli installed to bin/, mbim-proxy moved from libexec/) ──
check_version mbimcli
check_version mbim-proxy
check_help mbimcli

# ── 完整消费者用例（device-free 端到端功能流）────────────────────────────────
# mbimcli --printable 在设备检查之前执行，跑的是工具的核心完整链路：
#   hex 字符串 → MbimMessage 构造 → mbim_message_validate → 结构化 printable 输出
# 输入为一条合法的 MBIM_OPEN 报文（type=0x00000001, length=16, transaction=0,
# max_control_transfer=4096；MBIM 全部小端序）：
#   01000000 10000000 00000000 00100000
# 断言工具确实把报文解出了正确的报文头与内容字段（不止是退出码）。
MBIM_OPEN_MSG="01000000100000000000000000100000"
echo "----- mbimcli --printable <MBIM_OPEN> -----"
printable_out="$(mbimcli --printable "${MBIM_OPEN_MSG}")"
echo "${printable_out}"
for token in "Header:" "(0x00000001)" "max control transfer = 4096"; do
    case "${printable_out}" in
        *"${token}"*) echo "OK: decoded field present: ${token}" ;;
        *) echo "FAIL: mbimcli --printable output missing '${token}'" >&2; exit 1 ;;
    esac
done
echo "OK: mbimcli --printable decoded a full MBIM_OPEN message end-to-end"

# ── 负向：非法报文必须被拒绝（走完整的报文校验失败路径）──
# 报文头声明 length=4，小于 MBIM_OPEN 报文的最小长度（header 12 + open 4 = 16），
# mbim_message_validate 必须失败并以非零码退出。
echo "----- mbimcli --printable <invalid MBIM message> -----"
if mbimcli --printable "010000000400000000000000" > /dev/null 2>&1; then
    echo "FAIL: mbimcli --printable accepted an invalid MBIM message" >&2
    exit 1
fi
echo "OK: mbimcli --printable rejected an invalid MBIM message (declared length < header)"

echo "test_package: libmbim-tools ${VERSION} consumer test passed"
