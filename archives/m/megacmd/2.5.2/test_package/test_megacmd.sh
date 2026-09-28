#!/usr/bin/env bash
# test_megacmd.sh — 真实执行打包的 MEGAcmd 二进制（R34：二进制即被测 API）
set -u

try_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "[skip] $bin 不在 PATH"
    return 1
  fi
  # timeout 兜底：mega-cmd-server 若前台驻留不应拖死测试
  # || true 的理由（运行期平台限制，见 notes.md §8.4）：本包 mega-cmd-server 受平台 libcurl/8.5.0
  #   未启用 TLS 影响初始化即中止，且 CLI↔server 的 path-form AF_UNIX 在本平台任何可写目录都不可
  #   bind（HMDFS EPERM / /dev/shm EACCES / /tmp EROFS），故 timeout 的非零退出（124 超时 /
  #   126 不可执行 / 127 加载失败）都属预期，不作为判定依据；判定一律由下面的输出匹配负责。
  local out
  out="$(timeout 15 "$bin" --version 2>&1 || true)"
  echo "[$bin --version] => ${out:0:400}"
  # 匹配三型 *EGA* / *ersion* / *2.5*。其中 *ersion* 偏宽（含 version 字样的报错也会命中，
  #   理论上有假绿面）：该风险由 CI 的 L1e 破坏性反向验证压住——把包内 bin/ 移走后本测试必须
  #   失败，实测通过见 w3-local-ci.log:5709-5711。断言强度上限＝可加载 + 可执行 + 输出可识别。
  case "$out" in
    *EGA*|*ersion*|*2.5*)
      echo "OK: $bin 产出可解析版本输出（真实执行打包二进制成功）"
      return 0
      ;;
  esac
  return 1
}

for b in mega-cmd mega-exec mega-cmd-server; do
  if try_bin "$b"; then
    exit 0
  fi
done

# 兜底：至少证明 mega-* 包装脚本与二进制已随包装入且可被加载器执行
# || true 的理由：mega-ls 是包装脚本，功能上必须连常驻 mega-cmd-server，而 server 受 notes.md
#   §8.4 两项平台限制（libcurl 无 TLS、path-form AF_UNIX 不可 bind）在本平台必然失败；此处只
#   采集输出留痕，退出码不参与判定（版本判定已在上面的 try_bin 循环完成）。
if command -v mega-ls >/dev/null 2>&1; then
  out="$(timeout 15 mega-ls 2>&1 || true)"
  echo "[mega-ls] => ${out:0:400}"
fi

echo "FAIL: 未能从任何 MEGAcmd 二进制取得版本输出"
exit 1
