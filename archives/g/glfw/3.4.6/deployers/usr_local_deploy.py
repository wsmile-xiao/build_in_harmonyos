"""conan 自定义 deployer：把依赖图所有包展开到 output_folder(如 ~/usr/local)，
重定位 .pc 前缀，并为每个包写文件清单 + 生成可逆的卸载脚本。

用法:
    conan install --requires=cairo/1.18.0 -pr:h <profile> \
        --deployer=deployers/usr_local_deploy --deployer-folder=$HOME/usr/local
卸载:
    bash $HOME/usr/local/.conan-deployed/cairo-1.18.0-uninstall.sh
"""
import hashlib
import os
import re
import shutil

_SUBDIRS = ("include", "lib", "bin", "share")
_MANIFEST_DIR = ".conan-deployed"


def deploy(graph, output_folder, **kwargs):
    output_folder = str(output_folder)
    manifest_dir = os.path.join(output_folder, _MANIFEST_DIR)
    os.makedirs(manifest_dir, exist_ok=True)
    deployed = []
    for _require, dep in graph.root.conanfile.dependencies.items():
        pkg = getattr(dep, "package_folder", None)
        if not pkg:
            continue
        relpaths = _install_files(pkg, output_folder)
        ref = dep.ref
        deployed.append((str(ref.name), str(ref.version), relpaths))
    # 先重定位 .pc，再算 sha 写清单，保证校验值与落地内容一致
    _relocate_pc(output_folder)
    for name, version, relpaths in deployed:
        _write_manifest(manifest_dir, name, version, relpaths, output_folder)
        _emit_uninstall(manifest_dir, name, version)


def _install_files(pkg, output_folder):
    """把 pkg 的 include/lib/bin/share 拷进 output_folder，返回相对 pkg 的文件路径列表。"""
    copied = []
    for sub in _SUBDIRS:
        src = os.path.join(pkg, sub)
        if not os.path.isdir(src):
            continue
        for root, _dirs, files in os.walk(src):
            for fn in files:
                abs_src = os.path.join(root, fn)
                rel = os.path.relpath(abs_src, pkg)
                abs_dst = os.path.join(output_folder, rel)
                os.makedirs(os.path.dirname(abs_dst), exist_ok=True)
                shutil.copy2(abs_src, abs_dst)
                copied.append(rel)
    return copied


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_manifest(manifest_dir, name, version, relpaths, prefix):
    path = os.path.join(manifest_dir, "{}-{}.files".format(name, version))
    with open(path, "w", encoding="utf-8") as f:
        for rel in sorted(relpaths):
            abs_path = os.path.join(prefix, rel)
            sha = _sha256(abs_path) if os.path.isfile(abs_path) else ""
            f.write("{}\t{}\n".format(rel, sha))


def _emit_uninstall(manifest_dir, name, version):
    script = os.path.join(manifest_dir, "{}-{}-uninstall.sh".format(name, version))
    body = (_UNINSTALL_TEMPLATE
            .replace("__NAME__", name)
            .replace("__VERSION__", version)
            .replace("__MANIFEST__", "{}-{}.files".format(name, version)))
    with open(script, "w", encoding="utf-8") as f:
        f.write(body)
    os.chmod(script, 0o755)


_UNINSTALL_TEMPLATE = r'''#!/usr/bin/env bash
# 卸载 __NAME__-__VERSION__：按清单精确删除已部署文件，收空目录，绝不删整个前缀。
set -euo pipefail
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="$(cd "$SELF_DIR/.." && pwd)"
MANIFEST="$SELF_DIR/__MANIFEST__"
[ -f "$MANIFEST" ] || { echo "清单不存在: $MANIFEST" >&2; exit 1; }

removed=0; missing=0; changed=0
while IFS=$'\t' read -r rel sha; do
  [ -n "$rel" ] || continue
  f="$PREFIX/$rel"
  if [ ! -f "$f" ]; then missing=$((missing+1)); continue; fi
  if [ -n "$sha" ]; then
    if command -v sha256sum >/dev/null 2>&1; then
      cur="$(sha256sum "$f" | cut -d' ' -f1)"
    elif command -v shasum >/dev/null 2>&1; then
      cur="$(shasum -a 256 "$f" | cut -d' ' -f1)"
    else
      cur="$sha"
    fi
    if [ "$cur" != "$sha" ]; then
      echo "跳过(已被改动): $rel" >&2; changed=$((changed+1)); continue
    fi
  fi
  rm -f "$f"; removed=$((removed+1))
done < "$MANIFEST"

# 自底向上收空目录（只删变空的，不碰前缀本身）
while IFS=$'\t' read -r rel sha; do
  d="$PREFIX/$(dirname "$rel")"
  while [ "$d" != "$PREFIX" ] && [ -d "$d" ]; do
    rmdir "$d" 2>/dev/null || break
    d="$(dirname "$d")"
  done
done < "$MANIFEST"

rm -f "$MANIFEST" "$SELF_DIR/__NAME__-__VERSION__-uninstall.sh"
# 若本目录已无其它清单/脚本（最后一个包卸完），收掉空的 .conan-deployed/
rmdir "$SELF_DIR" 2>/dev/null || true
echo "卸载 __NAME__-__VERSION__ 完成：删除 ${removed}，缺失 ${missing}，跳过 ${changed}。"
'''


def _relocate_pc(prefix):
    """把 <prefix>/lib/pkgconfig 下所有 .pc 的 `prefix=` 行重写为 prefix（保留 ${prefix} 引用）。"""
    pc_dir = os.path.join(prefix, "lib", "pkgconfig")
    if not os.path.isdir(pc_dir):
        return
    for fn in os.listdir(pc_dir):
        if not fn.endswith(".pc"):
            continue
        path = os.path.join(pc_dir, fn)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        text = re.sub(r"(?m)^prefix=.*$", "prefix=" + prefix, text)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
