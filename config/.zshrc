export PATH=/storage/Users/currentUser/npm/bin:/storage/Users/currentUser/usr/local/bin:$PATH

export TMPDIR=$HOME/tmp


export CMAKE_PREFIX_PATH=$HOME/usr/local${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}

# ❌ 不要设置 C_INCLUDE_PATH / CPLUS_INCLUDE_PATH — 会与 pkg-config 冲突导致 --cflags 返回空
# ❌ 不要设置 LIBRARY_PATH — 会与构建系统冲突，用 LDFLAGS 或 PKG_CONFIG_PATH 代替

export LD_LIBRARY_PATH=$HOME/usr/local/lib:/data/service/hnp/magic-cli.org/magic-cli_1.0.0/lib:$LD_LIBRARY_PATH
export CPPFLAGS="-I$HOME/usr/local/include"
export DEFAULT_PREFIX=$HOME/usr/local
alias configure='./configure --prefix=$DEFAULT_PREFIX'
alias cmake='cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX'
alias Configure='./Configure --prefix=$DEFAULT_PREFIX'

export PERL5LIB="$HOME/perl-lib/lib/perl5:$PERL5LIB"

export AS="llvm-as"
export CC="clang"
export CC_FOR_BUILD="clang"
export CXX="clang++"
export LD="ld.lld"
export STRIP="llvm-strip"
export RANLIB="llvm-ranlib"
export OBJDUMP="llvm-objdump"
export OBJCOPY="llvm-objcopy"
export NM="llvm-nm"
export AR="llvm-ar"

# HarmonyOS: 所有编译都使用 -fPIC（共享库必需）
export CFLAGS="-fPIC -O2"
export CXXFLAGS="-fPIC -O2"
export LDFLAGS="-L$HOME/usr/local/lib"


alias ar='llvm-ar'
alias nm='llvm-nm'
alias objdump='llvm-objdump'
alias objcopy='llvm-objcopy'
alias strip='llvm-strip'
alias as='llvm-as'
alias ld='ld.lld'
alias link='llvm-link'

export OPENCLAW_CONFIG_PATH="~/.openclaw/claw.json"

# Python 3.12.9 HarmonyOS
export PATH="/storage/Users/currentUser/usr/python-3.12.9-ohos-aarch64/bin:$PATH"

# >>> Rust 1.89.0 HarmonyOS >>>
# Rust 1.89.0 HarmonyOS 环境变量
export PATH="/storage/Users/currentUser/usr/rust-1.89.0-aarch64-unknown-linux-ohos/bin:$PATH"
export RUST_HOME="/storage/Users/currentUser/usr/rust-1.89.0-aarch64-unknown-linux-ohos"
export CARGO_HOME="/storage/Users/currentUser/.cargo"
export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER=clang
export TMPDIR="${TMPDIR:-$HOME/tmp}"
export SSL_CERT_FILE="${SSL_CERT_FILE:-/etc/ssl/certs/cacert.pem}"
export OHOS_BINARY_SIGN_TOOL="/storage/Users/currentUser/usr/rust-1.89.0-aarch64-unknown-linux-ohos/tool/binary-sign-tool"
export CC="clang"
export CXX="clang++"
# <<< Rust 1.89.0 HarmonyOS <<<
