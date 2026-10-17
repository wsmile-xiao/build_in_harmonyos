export PATH=/storage/Users/currentUser/npm/bin:/storage/Users/currentUser/usr/local/bin:$PATH
export TMPDIR=$HOME/tmp
export CMAKE_PREFIX_PATH=$HOME/usr/local${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}
export LD_LIBRARY_PATH=$HOME/usr/local/lib:/data/service/hnp/magic-cli.org/magic-cli_1.0.0/lib:$LD_LIBRARY_PATH
export DEFAULT_PREFIX=$HOME/usr/local
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
export CFLAGS="-fPIC -O2"
export CXXFLAGS="-fPIC -O2"
export LDFLAGS="-L$HOME/usr/local/lib"
export CPPFLAGS="-I$HOME/usr/local/include"
alias configure='./configure --prefix='
alias cmake='cmake -DCMAKE_INSTALL_PREFIX='
alias Configure='./Configure --prefix='
alias ar='llvm-ar'
alias nm='llvm-nm'
alias objdump='llvm-objdump'
alias objcopy='llvm-objcopy'
alias strip='llvm-strip'
alias as='llvm-as'
alias ld='ld.lld'
alias link='llvm-link'
export AGENT_NAME=runner003
