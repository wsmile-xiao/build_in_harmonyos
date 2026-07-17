#!/bin/bash
# ============================================================================
# build_ohos.sh — ent (Go entity framework) for OpenHarmony PC aarch64
#
# 功能:
#   1. 自动下载 ent 官方源码
#   2. 适配 OpenHarmony PC aarch64 交叉编译 (Go + CGo)
#   3. 静态编译，输出 entc 二进制
#
# 用法:
#   bash build_ohos.sh [version] [prefix]
#
# 环境变量:
#   GOOS / GOARCH — 目标 OS 和架构 (默认 linux / arm64)
#   CC           — C 编译器 (默认 aarch64-linux-ohos-clang)
#   CGO_ENABLED  — 是否启用 CGo (默认 1)
#   GOPROXY      — Go 模块代理 (默认 https://goproxy.io,direct)
#
# 前置依赖 (OHOS 设备):
#   - Go 1.21+
#   - aarch64-linux-ohos-clang (OHOS NDK)
#   - git
# ============================================================================

set -euo pipefail

# ---- 版本与路径 ------------------------------------------------------------
ENT_VERSION="${1:-0.14.6}"
PREFIX="${2:-$HOME/usr/local}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$HOME/tmp/build-ent-$$"
STAGING_DIR="$BUILD_DIR/staging"
PKG_DIR="$BUILD_DIR/pkg"

# ---- 交叉编译环境 ----------------------------------------------------------
GOOS="${GOOS:-linux}"
GOARCH="${GOARCH:-arm64}"
CC="${CC:-aarch64-linux-ohos-clang}"
CGO_ENABLED="${CGO_ENABLED:-1}"
GOPROXY="${GOPROXY:-https://goproxy.io,direct}"

# ============================================================================
# 辅助函数
# ============================================================================

log()  { printf "\033[1;32m[INFO]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
err()  { printf "\033[1;31m[ERROR]\033[0m %s\n" "$*" >&2; exit 1; }

cleanup() {
    log "清理临时目录: $BUILD_DIR"
    rm -rf "$BUILD_DIR"
}
trap cleanup EXIT

check_deps() {
    command -v go &>/dev/null || err "需要安装 Go (https://go.dev/dl/)"
    command -v git &>/dev/null || err "需要安装 git"
    if [ "$CGO_ENABLED" = "1" ]; then
        command -v "$CC" &>/dev/null || warn "未找到 $CC，CGo 编译可能失败，尝试 CGO_ENABLED=0"
    fi
}

# ============================================================================
# 主流程
# ============================================================================

log "=== ent $ENT_VERSION → ${GOOS}/${GOARCH} 交叉编译 ==="
log "编译器: $CC"
log "CGo:    $CGO_ENABLED"
log "安装到: $PREFIX"

check_deps

mkdir -p "$BUILD_DIR" "$STAGING_DIR/bin" "$PKG_DIR"

# ---- Step 1: 下载源码 ------------------------------------------------------
log "Step 1/5: 下载 ent $ENT_VERSION 源码..."

cd "$BUILD_DIR"
if [ -d "$BUILD_DIR/ent" ]; then
    log "源码已存在，更新..."
    cd "$BUILD_DIR/ent" && git pull
else
    if ! git clone --depth 1 --branch "v${ENT_VERSION}" \
        https://github.com/ent/ent.git "$BUILD_DIR/ent"; then
        err "无法克隆上游标签 v${ENT_VERSION}；请检查版本号、网络或认证状态。为避免构建错误版本，脚本不会回退到默认分支。"
    fi
fi

cd "$BUILD_DIR/ent"
log "源码目录: $(pwd)"

# ---- Step 2: 进入 cmd/entc ------------------------------------------------
log "Step 2/5: 定位 entc 入口..."

ENTC_DIR="$BUILD_DIR/ent/cmd/entc"
if [ ! -d "$ENTC_DIR" ]; then
    # 尝试查找 main.go
    MAIN_FILE=$(find "$BUILD_DIR/ent" -name "main.go" -path "*/cmd/*" | head -1)
    if [ -n "$MAIN_FILE" ]; then
        ENTC_DIR=$(dirname "$MAIN_FILE")
        log "自动发现入口: $ENTC_DIR"
    else
        # 没有 cmd 子目录时，项目本身可能直接是 main 包
        ENTC_DIR="$BUILD_DIR/ent"
        log "使用项目根目录: $ENTC_DIR"
    fi
fi

# ---- Step 3: 编译 ----------------------------------------------------------
log "Step 3/5: 交叉编译 entc (${GOOS}/${GOARCH})..."

cd "$ENTC_DIR"

# R33: 使用环境变量而非 go env -w（避免修改全局配置）
export GO111MODULE=on
export GOPROXY="$GOPROXY"

GOOS="$GOOS" GOARCH="$GOARCH" CC="$CC" CGO_ENABLED="$CGO_ENABLED" \
    go build \
    -ldflags="-s -w -extldflags=-static" \
    -tags osusergo,netgo \
    -o "$STAGING_DIR/bin/entc" \
    . || err "go build 失败"

# ---- Step 4: 验证二进制 ----------------------------------------------------
log "Step 4/5: 验证..."

if [ -f "$STAGING_DIR/bin/entc" ]; then
    file "$STAGING_DIR/bin/entc"
    chmod +x "$STAGING_DIR/bin/entc"
    log "✅ entc 编译成功"
else
    err "entc 未生成"
fi

# ---- Step 5: 安装与打包 ----------------------------------------------------
log "Step 5/5: 安装到 $PREFIX 并打包..."

mkdir -p "$PREFIX/bin"
cp "$STAGING_DIR/bin/entc" "$PREFIX/bin/entc"
chmod +x "$PREFIX/bin/entc"

# 打包
PKG_NAME="ent-${ENT_VERSION}-ohos-aarch64"
PKG_TAR="$PKG_DIR/${PKG_NAME}.tar.gz"
cd "$STAGING_DIR"
tar czf "$PKG_TAR" bin/
log "✅ 包已创建: $PKG_TAR"

# PATH 提示
if ! grep -q 'usr/local/bin' "$HOME/.zshrc" 2>/dev/null; then
    warn "建议将 $PREFIX/bin 加入 PATH:"
    warn "  echo 'export PATH=\"$PREFIX/bin:\$PATH\"' >> ~/.zshrc"
fi

# ---- 验证 ----------------------------------------------------------------
log "=== 验证 ==="
"$PREFIX/bin/entc" --help 2>/dev/null && log "✅ entc 运行正常" || \
    warn "⚠️  entc 无法运行，可能缺少 C 运行时库"

echo ""
echo "=============================="
echo " ent $ENT_VERSION 构建完成"
echo " 目标:   ${GOOS}/${GOARCH}"
echo " 安装到: $PREFIX"
echo " 包:     $PKG_TAR"
echo "=============================="
