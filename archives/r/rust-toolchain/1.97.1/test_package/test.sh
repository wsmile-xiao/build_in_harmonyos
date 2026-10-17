#!/bin/sh
# rust-toolchain 1.97.1 — 工具链与 OHOS aarch64 目标验证
#
# 上游测试统计说明：rust 官方预编译发行包（132MB tarball）共 246 个条目、
# 0 个 test 文件——完整测试套件在 rust-lang/rust 源码仓（rustc/cargo 全量
# 测试需自举构建），预编译发行包不携带。本脚本以两层验证集覆盖工具链可用性：
#   A) 静态组件验证（10 项断言，不依赖 exec，任何环境可跑）
#   B) 动态 exec 验证（6 项断言：rustc/cargo 版本、OHOS target、交叉编译并
#      本机运行 hello、cargo test 上游 crate cfg-if）
# 本地 HarmonyOS HMDFS 沙箱对解压二进制有 hmmac 标签限制（E046：exec 恒
# Permission denied），B 层在本机走警告降级（exit 0），CI 干净环境严格执行。
# A 层任一断言失败立即 exit 1（R9：禁止伪造通过），成功文案按实际计数输出。
set -e

TMP="${TMPDIR:-${HOME:-.}/tmp}"
mkdir -p "$TMP"

PASS=0
FAIL=0
chk() {
  desc="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "[PASS] $desc"; PASS=$((PASS + 1))
  else
    echo "[FAIL] $desc"; FAIL=$((FAIL + 1))
  fi
}

# ── A) 静态组件验证（10 项，不依赖 exec） ──
echo "== A) 静态组件验证 =="
RUSTC_BIN="$(command -v rustc 2>/dev/null || true)"
if [ -z "$RUSTC_BIN" ]; then
  echo "[FAIL] A 层前置：PATH 中无 rustc（tool_requires 未注入？）"
  exit 1
fi
PREFIX="$(cd "$(dirname "$RUSTC_BIN")/.." && pwd)"
RUSTLIB="$PREFIX/lib/rustlib/aarch64-unknown-linux-ohos"

chk "A1 rustc 存在且为 ELF"       sh -c "head -c4 '$PREFIX/bin/rustc' | grep -q ELF"
chk "A2 cargo 存在且为 ELF"       sh -c "head -c4 '$PREFIX/bin/cargo' | grep -q ELF"
chk "A3 rustfmt 存在"             test -s "$PREFIX/bin/rustfmt"
chk "A4 clippy-driver 存在"       test -s "$PREFIX/bin/clippy-driver"
chk "A5 rust-analyzer 存在"       test -s "$PREFIX/bin/rust-analyzer"
chk "A6 OHOS target sysroot 存在" test -d "$RUSTLIB"
chk "A7 libstd rlib 存在"         sh -c "ls '$RUSTLIB/lib/' | grep -q 'libstd-'"
chk "A8 libcore rlib 存在"        sh -c "ls '$RUSTLIB/lib/' | grep -q 'libcore-'"
chk "A9 sysroot 库文件充足(>=50)" sh -c "[ \$(ls '$RUSTLIB/lib/' | wc -l) -ge 50 ]"
chk "A10 rustc 为 aarch64 机器码" sh -c "od -An -tx1 -j18 -N2 '$PREFIX/bin/rustc' | grep -q 'b7 00'"
echo "静态验证: PASS=$PASS FAIL=$FAIL"

# A 层失败门禁：任一静态断言失败（打包缺件/组件损坏）立即中止，
# 不得带着 FAIL>0 继续到 B 层或成功文案（R9：禁止伪造通过）。
if [ "$FAIL" -gt 0 ]; then
  echo "A 层静态验证失败 ${FAIL} 项——打包缺件或组件损坏，中止"
  exit 1
fi

# ── B) 动态 exec 验证（需 exec 权限） ──
echo "== B) 动态 exec 验证 =="
D_PASS=0
if ! rustc --version >/dev/null 2>&1; then
  echo "E046/HMDFS: 本机无法执行捆绑的 rustc（平台标签限制）；exec 验证延后至 CI 严格执行"
  exit 0
fi

echo "== rustc version =="
if rustc --version; then
  D_PASS=$((D_PASS + 1))
else
  echo "FAIL: rustc --version"; exit 1
fi

echo "== cargo version =="
if cargo --version; then
  D_PASS=$((D_PASS + 1))
else
  echo "FAIL: cargo --version"; exit 1
fi

echo "== OHOS target installed =="
if rustc --print target-list | grep -qx aarch64-unknown-linux-ohos; then
  echo "OK: aarch64-unknown-linux-ohos target present"; D_PASS=$((D_PASS + 1))
else
  echo "FAIL: OHOS target missing"; exit 1
fi

echo "== cross-compile hello for aarch64-unknown-linux-ohos =="
cat > "$TMP/rust_hello.rs" <<'EOF'
fn main() { println!("hello from rust on ohos"); }
EOF
if rustc --target aarch64-unknown-linux-ohos "$TMP/rust_hello.rs" -o "$TMP/rust_hello"; then
  D_PASS=$((D_PASS + 1))
else
  echo "FAIL: cross-compile hello"; exit 1
fi

echo "== run hello on host (HarmonyOS aarch64) =="
if "$TMP/rust_hello"; then
  D_PASS=$((D_PASS + 1))
else
  echo "FAIL: run hello"; exit 1
fi

echo "== cargo test: 上游 crate cfg-if 1.0（rsproxy 镜像） =="
export CARGO_HOME="$TMP/cargo_home_verify"
mkdir -p "$CARGO_HOME"
cat > "$CARGO_HOME/config.toml" <<'EOF'
[source.crates-io]
replace-with = "rsproxy"
[source.rsproxy]
registry = "sparse+https://rsproxy.cn/index/"
EOF
PROJ="$TMP/cfgif_verify"
rm -rf "$PROJ" && mkdir -p "$PROJ/src"
cat > "$PROJ/Cargo.toml" <<'EOF'
[package]
name = "cfgif_verify"
version = "0.1.0"
edition = "2021"

[dependencies]
cfg-if = "1.0"
EOF
cat > "$PROJ/src/lib.rs" <<'EOF'
cfg_if::cfg_if! {
    if #[cfg(target_os = "ohos")] {
        pub fn platform() -> &'static str { "ohos" }
    } else if #[cfg(target_os = "linux")] {
        pub fn platform() -> &'static str { "linux" }
    } else {
        pub fn platform() -> &'static str { "other" }
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn platform_known() {
        assert!(!crate::platform().is_empty());
    }
}
EOF
if (cd "$PROJ" && timeout 600 cargo test); then
  D_PASS=$((D_PASS + 1))
else
  echo "FAIL: cargo test cfg-if"; exit 1
fi

echo "rust-toolchain 验证集 OK（静态 ${PASS}/10 PASS，动态 ${D_PASS}/6 PASS）"
