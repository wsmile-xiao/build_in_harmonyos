#!/data/service/hnp/bin/bash
# setup-el2-runtime.sh —— grantlee test_package 的 el2 运行时布置脚本
#
# HarmonyOS 平台上 musl 加载器拒绝加载 HMDFS 路径（/storage/Users/...，
# 含 conan 缓存 ~/.conan2/p/）上构建的部分 .so（dlopen: Permission denied，
# 自带 .codesign 段但本机加载器不认——重签后可加载，见 HarmonyOS 恢复
# 知识库 exec-permission 条目与知识草稿
# DRAFT-libkysdk-system-3.0.1.1-hmdfs-el2-runtime-copy）。
#
# test() 运行前调用本脚本：把 grantlee 与 qt5-qtbase 的运行库/插件拷贝到
# el2 应用数据目录（/data/storage/el2/base/files——应用数据类型，签名后
# 可正常加载），三段式 SONAME 软链实体化展开（E316/E492），并全量重签
#（binary-sign-tool 自签，同 CI sign.sh 流程；SDK 原生的 libc++_shared.so
# 无 .codesign 段且签名有效，跳过）。
#
# 用法：setup-el2-runtime.sh <grantlee包目录> <qt5-qtbase包目录>
set -u
E=/data/storage/el2/base/files/.conan-runlibs/grantlee
SDK_LIBCPP=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos/libc++_shared.so
B=/data/service/hnp/bin/binary-sign-tool
OC=/data/service/hnp/bin/llvm-objcopy

PKG=${1:?grantlee package folder required}
QT=${2:?qt5-qtbase package folder required}

# 幂等哨兵：库集合指纹（两包目录 + 文件数）未变则跳过重建
SIG=$(ls "$PKG/lib" 2>/dev/null | md5sum | cut -d' ' -f1)-$(ls "$QT/lib" 2>/dev/null | md5sum | cut -d' ' -f1)
if [ -f "$E/.ready" ] && [ "$(cat "$E/.ready" 2>/dev/null)" = "$SIG" ]; then
  exit 0
fi

rm -rf "$E"
mkdir -p "$E"

# libc++_shared（SDK 原生签名，不重签）
[ -f "$SDK_LIBCPP" ] && cp "$SDK_LIBCPP" "$E/" && chmod 755 "$E/libc++_shared.so"

# qt5-qtbase 全部 .so（-L 实体化三段链）
for f in $(ls "$QT/lib" 2>/dev/null | grep -E "^libQt5.*\.so"); do
  cp -L "$QT/lib/$f" "$E/" 2>/dev/null || true
done
# grantlee 包内库
for f in $(ls "$PKG/lib" 2>/dev/null | grep -E "\.so"); do
  cp -L "$PKG/lib/$f" "$E/" 2>/dev/null || true
done
# 插件树（引擎查找布局 <pluginDir>/grantlee/<major>.<minor>/）
mkdir -p "$E/grantlee-plugins"
cp -rL "$PKG/lib/grantlee" "$E/grantlee-plugins/" 2>/dev/null || true
chmod -R 755 "$E" 2>/dev/null || true

# 全量重签（libc++_shared 除外）
if [ -x "$B" ] && [ -x "$OC" ]; then
  find "$E" -name "*.so*" -type f 2>/dev/null | while read -r f; do
    base=$(basename "$f")
    [ "$base" = "libc++_shared.so" ] && continue
    rm -f "$f.unsigned"
    if "$OC" --remove-section=.codesign "$f" "$f.unsigned" 2>/dev/null; then
      if "$B" sign -selfSign 1 -inFile "$f.unsigned" -outFile "$f" \
          -signAlg SHA256withECDSA >/dev/null 2>&1; then
        chmod 755 "$f"
      fi
    fi
    rm -f "$f.unsigned"
  done
fi

echo "$SIG" > "$E/.ready"
exit 0
