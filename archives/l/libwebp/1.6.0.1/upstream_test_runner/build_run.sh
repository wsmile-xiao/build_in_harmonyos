#!/bin/sh
# 真机:静态构建上游 libwebp + 12 个 fuzz 目标驱动,并逐个运行。
# 前置:本目录已解包到 ~/fuzzrun(libwebp-1.6.0 源码树随包);
#       conan 缓存 libwebp 1.6.0.1 的 generators 提供 OHOS 工具链。
set -e

PKG="/storage/Users/currentUser/.conan2/p/b/libwef50c167350a06"
TF="$PKG/b/build/Release/generators/conan_toolchain.cmake"
SRC="$HOME/fuzzrun/libwebp-1.6.0"
if [ ! -d "$SRC/src" ]; then
  echo "SRC-MISSING $SRC" >&2
  exit 1
fi
if [ ! -f "$TF" ]; then
  echo "TOOLCHAIN-FILE-NOT-FOUND $TF" >&2
  exit 1
fi
echo "TOOLCHAIN=$TF"
echo "SRC=$SRC"

cd "$HOME/fuzzrun"

# 种子语料以 base64 文本入库(平台 PR diff 管线不支持二进制补丁,见本目录 README),
# 运行前用 python3 解码还原到 seeds_bin/,并打印 md5(与 seeds_md5.txt 互证字节一致)。
python3 - <<'PYEOF'
import base64, hashlib, os
os.makedirs("seeds_bin", exist_ok=True)
for fn in sorted(os.listdir("seeds_b64")):
    if not fn.endswith(".b64"):
        continue
    raw = open(os.path.join("seeds_b64", fn), "rb").read()
    data = base64.b64decode(raw)
    with open(os.path.join("seeds_bin", fn[:-4]), "wb") as f:
        f.write(data)
    print("decoded %-24s %6d bytes  md5=%s" % (fn[:-4], len(data), hashlib.md5(data).hexdigest()))
PYEOF

cmake -S . -B build -G Ninja \
      -DCMAKE_TOOLCHAIN_FILE="$TF" \
      -DWEBP_SRC_ROOT="$SRC" \
      -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 8

sh run_all.sh
