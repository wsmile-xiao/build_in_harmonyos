# mmh-fix 设备环境（source 使用）
export CONAN_HOME="${CONAN_HOME:-$HOME/.conan2}"
export TMPDIR="$HOME/tmp"
mkdir -p "$TMPDIR"
HNP=/data/service/hnp/bin
export PATH="$HNP:$PATH"
export CONFIG_SHELL="$HNP/bash"
export SHELL="$HNP/bash"
