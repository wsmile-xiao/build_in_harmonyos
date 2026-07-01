#!/usr/bin/env bash
# make-package.sh — 探测 OS → 选 conan profile → conan create [+ upload]。
# macOS → 交叉编译(host=ohos)；鸿蒙 PC/其它 → 原生编译(build=host=ohos)。
# 用法: bash make-package.sh [--upload] [--remote-url URL]
set -euo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_NAME="ohos-conan"
REMOTE_URL="${CONAN_REMOTE_URL:-https://cnb.cool/OpenHarmonyPCDeveloper/Conan}"
DO_UPLOAD=0

while [ $# -gt 0 ]; do
  case "$1" in
    --upload) DO_UPLOAD=1; shift;;
    --remote-url) REMOTE_URL="$2"; shift 2;;
    *) echo "make-package.sh: 未知参数: $1" >&2; exit 1;;
  esac
done

die() { echo "[make-package] ✗ $*" >&2; exit 1; }

# 前置自检：缺依赖时给清晰提示，别等 conan 半路报晦涩错误（尤其鸿蒙 PC 首跑）。
preflight() {
  command -v conan >/dev/null 2>&1 || die "缺少 conan（装 conan 2.x：pip install conan）"
  # conan settings 需含 os=OHOS（团队约定大写）
  conan config home >/dev/null 2>&1 || die "conan 无法初始化（检查 conan 安装）"
  # 签名器（package() 会调 scripts/sign-so.sh）：三选一，与 sign-so.sh 解析一致
  #   原生 binary-sign-tool（SIGN_TOOL 或 PATH，鸿蒙 PC 无需 java）｜ mac 的 java+jar
  #   SKIP_SIGN 非空则跳过检查（仅限本机不运行 .so 的验证场景，如 mac 交叉）
  if [ -n "${SKIP_SIGN:-}" ]; then
    echo "[make-package] ⚠ SKIP_SIGN 已设：跳过签名（仅验证编译/链接，勿用于设备/发布）"
  elif [ -n "${SIGN_TOOL:-}" ] && [ -x "$SIGN_TOOL" ]; then :
  elif command -v binary-sign-tool >/dev/null 2>&1; then :
  else
    local deveco="${DEVECO:-/Applications/DevEco-Studio.app}"
    local java="${JAVA:-$deveco/Contents/jbr/Contents/Home/bin/java}"
    local jar="${JAR:-$deveco/Contents/sdk/default/openharmony/toolchains/lib/binary-sign-tool.jar}"
    { [ -x "$java" ] && [ -f "$jar" ]; } || \
      die "找不到签名器：设 SIGN_TOOL=<binary-sign-tool 路径>，或把原生 binary-sign-tool 放进 PATH（鸿蒙 PC 无需 java），或(mac) 设 DEVECO/JAVA/JAR，或 SKIP_SIGN=1 仅验证编译"
  fi
}

OS="$(uname -s)"
case "$OS" in
  Darwin)
    echo "[make-package] macOS → 交叉编译 (host=ohos)"
    [ -n "${OHOS_NDK_HOME:-}" ] || die "需设置 OHOS_NDK_HOME 指向已装 OHOS SDK 的 native ndk"
    [ -f "$OHOS_NDK_HOME/build/cmake/ohos.toolchain.cmake" ] || die "OHOS_NDK_HOME 无效（缺 build/cmake/ohos.toolchain.cmake）: $OHOS_NDK_HOME"
    PROFILES=(-pr:b default -pr:h "$SELF_DIR/profiles/ohos-cross")
    ;;
  *)
    echo "[make-package] $OS → 原生编译 (build=host=ohos，用 OHOS SDK toolchain)"
    # 原生也走 ohos.toolchain.cmake（正确 sysroot/系统名/宏，避免 'System unknown'、CLOCK_* 缺失）
    [ -n "${OHOS_NDK_HOME:-}" ] || die "需设置 OHOS_NDK_HOME 指向设备 OHOS SDK 的 native 目录"
    [ -f "$OHOS_NDK_HOME/build/cmake/ohos.toolchain.cmake" ] || die "OHOS_NDK_HOME 无效（缺 build/cmake/ohos.toolchain.cmake）: $OHOS_NDK_HOME"
    # build 与 host 都用 ohos-native（同一 profile → 非交叉），避免依赖设备上不存在的 default profile
    PROFILES=(-pr:b "$SELF_DIR/profiles/ohos-native" -pr:h "$SELF_DIR/profiles/ohos-native")
    ;;
esac

preflight

conan create "$SELF_DIR" "${PROFILES[@]}" --build=missing

if [ "$DO_UPLOAD" = "1" ]; then
  conan remote add "$REMOTE_NAME" "$REMOTE_URL" 2>/dev/null || true
  conan upload "glfw/3.4.6" -r "$REMOTE_NAME" --confirm
fi
