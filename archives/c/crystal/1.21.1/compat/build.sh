#!/bin/sh
# crystal 构建驱动脚本（在 conan build() 中被调用）。
#
# 为什么用脚本而不是在 conanfile 里拼 self.run(cmd, env=[...])：
# 实测同一套环境变量在**手动导出**时可正常构建（编译出 47 MB 可用编译器），
# 但在 conan 的 `self.run(env=[...])` 下**未生效**——crystal 的编译期宏
# （src/llvm/lib_llvm.cr:23 的 `env("LLVM_LDFLAGS")`）仍取不到值，退回去跑
# `llvm-config --libs`，于是列出 110 个 SDK 里不存在的组件库并刷屏报错。
# 把导出集中到本脚本由 shell 执行，可完全绕开该差异。
#
# 由 conanfile 通过环境变量传入各路径：
#   CR_SRC       源码树
#   CR_BOOT      bootstrap 根（含 bin/crystal、bin/shards、share/crystal/src）
#   CR_LDFLAGS  依赖 -L 与 compat 垫片对象
#   CR_PATH      PATH 前缀（含 llvm-config 包装器目录）
#   CR_LLVM_MONO 单体 libLLVM 的 -L 路径
#   CR_PKGCFG    PKG_CONFIG_PATH
#   CR_CFLAGS    依赖 -isystem

# -e：任一命令失败即中止（原状）；-u：引用未定义变量即报错，避免把空值
# 当成"探测成功"继续构建（例如 CR_LLVMCFG_DIR 为空会让 PATH 前置退化成
# 当前目录，进而静默命中错误的 llvm-config）。
set -eu
# pipefail：非 POSIX 必备项，早期 mksh/sash 不支持。探测失败不影响后续，
# 故用 if 条件（set -e 不对条件求值生效）而非 || true，保持语义清晰。
if (set -o pipefail) 2>/dev/null; then set -o pipefail; fi

echo "[cr-build] SRC=$CR_SRC"
echo "[cr-build] BOOT=$CR_BOOT"

# ── 1) LLVM：用包装器把 --libs 的答案换成单体库 ────────────────────────
# OHOS SDK 只有 libLLVM.so / libLLVM-15.so / libLLVM-15.0.4.so 三个单体库，
# 而真实 llvm-config --libs 会列 110 个组件库 → lld 刷屏 "unable to find
# library -lLLVMXxx"。包装器已由 conanfile 放入 $CR_LLVMCFG_DIR 并命名为
# llvm-config，这里把它放到 PATH 最前，确保 crystal 的编译期宏命中。
export PATH="$CR_LLVMCFG_DIR:$CR_PATH:$PATH"
export LLVM_CONFIG="$CR_LLVMCFG_DIR/llvm-config"
# 双保险：lib_llvm.cr:23 优先取 LLVM_LDFLAGS，若该变量可见则直接短路
export LLVM_LDFLAGS="-L$CR_LLVM_MONO -lLLVM-15.0.4"
# 让运行时也能找到 libLLVM（crystal 可执行体动态依赖它）
export LD_LIBRARY_PATH="$CR_LLVM_MONO:$CR_LDLIBDIRS:${LD_LIBRARY_PATH:-}"

# ── 2) 依赖探测：OpenSSL 版本判定依赖 pkg-config ───────────────────────
# 未设 PKG_CONFIG_PATH 时 crystal 探测静默退化为 "0.0.0"，走 OpenSSL 1.1
# 裸名分支，逐个报 sk_value/sk_pop_free/EVP_CIPHER_flags undefined。
export PKG_CONFIG_PATH="$CR_PKGCFG"

# ── 3) stdlib 搜索路径 ────────────────────────────────────────────────
# 必须同时含 lib（shards）、src、src/lib_c/<triple>，缺任一个即报
# "can't find file 'markd'" 或 "can't find file 'c/fcntl'"。
export CRYSTAL_PATH="$CR_SRC/lib:$CR_SRC/src:$CR_SRC/src/lib_c/aarch64-linux-musl:$CR_BOOT/share/crystal/src"

export CFLAGS="$CR_CFLAGS"
export CXXFLAGS="$CR_CFLAGS"

cd "$CR_SRC"

# ── 4) 打印关键变量，便于失败时定位（不打印任何凭据）─────────────────
echo "[cr-build] llvm-config -> $(command -v llvm-config)"
echo "[cr-build] llvm-config --libs -> $(llvm-config --libs)"
echo "[cr-build] pkg-config libcrypto -> $(pkg-config --modversion libcrypto 2>&1)"

# ── 5) 构建编译器 ────────────────────────────────────────────────────
# --jobserver-style=pipe: HMDFS 不支持 mkfifo（make 默认 jobserver 用 fifo）
exec "$CR_MAKE" --jobserver-style=pipe -j"$CR_JOBS" crystal \
    CRYSTAL="$CR_BOOT/bin/crystal" \
    FLAGS="--target aarch64-unknown-linux-musl" \
    LDFLAGS="$CR_LDFLAGS"
