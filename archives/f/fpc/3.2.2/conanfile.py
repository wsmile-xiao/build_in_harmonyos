#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe: Free Pascal Compiler (FPC) 3.2.2 for HarmonyOS PC (aarch64).

Adaptation notes
----------------
FPC 3.2.2 has no native `ohos` target (its rtl/ and compiler/systems/ only
provide linux/android), and building FPC from source needs a GNU as/ld for the
target, which an OpenHarmony worker does not guarantee. The official FPC 3.2.2
compiler binaries are statically linked, so the official aarch64-linux release
runs natively on OHOS aarch64. This recipe therefore assembles the upstream
aarch64-linux distribution (compiler + RTL + packages), verifies every input
against its pinned SHA256 digest, adds a relocatable `fpc` launcher and ships
the matching upstream source tree so that downstream consumers (lazarus) can
point FPCDIR at a directory containing rtl/.

FPC's AArch64 code generator emits GNU-as syntax and calls an external
assembler/linker; OHOS ships LLVM rather than GNU binutils, so the package also
ships small `as`/`ld` bridges that prefer a real AArch64 GNU tool and fall back
to the platform C compiler (integrated assembler) and lld.
"""
import hashlib
import json
import os
import shutil
import stat
import tarfile
import threading
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                              export_conandata_patches, get, save)
from conan.tools.layout import basic_layout

_TARGET = "aarch64-linux"

_LAUNCHER = r'''#!/bin/sh
# Relocatable launcher for the Conan-packaged Free Pascal Compiler.
# The official upstream driver is kept next to it as "fpc-driver"; this
# wrapper resolves the package root from its own path, wires up the packaged
# unit search paths and points FPC at the packaged as/ld bridges, so the
# package works from any Conan cache location.
self="$0"
case "$self" in
  */*) ;;
  *) self="$(command -v -- "$self" 2>/dev/null || printf '%s' "$self")" ;;
esac
while [ -h "$self" ]; do
  dir=$(cd -P "$(dirname "$self")" && pwd)
  link=$(readlink "$self")
  case "$link" in
    /*) self="$link" ;;
    *)  self="$dir/$link" ;;
  esac
done
bindir=$(cd -P "$(dirname "$self")" && pwd)
root=$(cd -P "$bindir/.." && pwd)
fpcdir="$root/lib/fpc/@FPCVER@"
units="$fpcdir/units/@TARGET@"
tooldir="$root/libexec/fpc-toolchain"
export PATH="$bindir:$fpcdir:$PATH"
if [ "$#" -gt 0 ] && { [ "$1" = "--version" ] || [ "$1" = "-version" ]; }; then
  set -- -iV
fi
if [ -d "$tooldir" ]; then
  exec "$bindir/fpc-driver" -FD"$tooldir" -Fu"$units" -Fu"$units/rtl" -Fu"$units/*" "$@"
fi
exec "$bindir/fpc-driver" -Fu"$units" -Fu"$units/rtl" -Fu"$units/*" "$@"
'''

_AS_SHIM = r'''#!/bin/sh
# Assembler bridge for the packaged Free Pascal compiler.
# FPC's AArch64 code generator emits GNU-as syntax and invokes an external
# "as". Prefer a real AArch64 GNU assembler; otherwise use the platform C
# compiler's integrated assembler (OHOS ships clang/LLVM, not GNU binutils).
CC="@CC@"
for c in aarch64-unknown-linux-ohos-as aarch64-linux-gnu-as; do
  if command -v "$c" >/dev/null 2>&1; then exec "$c" "$@"; fi
done
if [ -n "$CC" ] && [ -x "$CC" ]; then
  exec "$CC" -c "$@"
fi
for d in $LD_LIBRARY_PATH; do
  cand=$(printf '%s' "$d" | sed 's#/lib$#/bin/clang#')
  if [ -x "$cand" ]; then exec "$cand" --target=aarch64-linux-ohos -c "$@"; fi
done
if command -v clang >/dev/null 2>&1; then
  exec clang --target=aarch64-linux-ohos -c "$@"
fi
if command -v as >/dev/null 2>&1; then exec as "$@"; fi
echo "fpc: no usable AArch64 assembler found" >&2
exit 1
'''

_LD_SHIM = r'''#!/bin/sh
# Linker bridge for the packaged Free Pascal compiler.
CCDIR="@CCDIR@"
if [ -n "$CCDIR" ] && [ -x "$CCDIR/ld.lld" ]; then exec "$CCDIR/ld.lld" "$@"; fi
for d in $LD_LIBRARY_PATH; do
  cand=$(printf '%s' "$d" | sed 's#/lib$#/bin/ld.lld#')
  if [ -x "$cand" ]; then exec "$cand" "$@"; fi
done
for c in aarch64-unknown-linux-ohos-ld aarch64-linux-gnu-ld ld.lld lld; do
  if command -v "$c" >/dev/null 2>&1; then exec "$c" "$@"; fi
done
if command -v ld >/dev/null 2>&1; then exec ld "$@"; fi
echo "fpc: no usable AArch64 linker found" >&2
exit 1
'''


# Bounded parallel source download. The CI worker link to
# downloads.freepascal.org / downloads.sourceforge.net moves at ~10-20 KB/s and
# drops mid-transfer, so a plain tools.files.get() either stalls past the outer
# timeout or dies with IncompleteRead.  Fetch the release inputs ourselves:
# parallel HTTP range chunks (a single stalled flow no longer caps the whole
# transfer), per-chunk retry/resume, and a pinned SHA256 over the assembly.
# A finished download lands in the Conan source-download cache (DOWNLOAD_CACHE,
# layout s/<sha256>) so the next build is served locally with no network.
_UA = "ohpcd-conan-source/1.0"
_PART_MIN = 4 * 1024 * 1024
_PART_COUNT = int(os.environ.get("FPC_DL_PARTS", "8"))
_PART_RETRIES = int(os.environ.get("FPC_DL_RETRIES", "5"))
_READ_TIMEOUT = int(os.environ.get("FPC_DL_READ_TIMEOUT", "60"))


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _archive_ok(path, sha256):
    try:
        return (os.path.isfile(path) and os.path.getsize(path) > 0
                and _sha256_file(path) == sha256)
    except OSError:
        return False


def _http_get(url, headers=None):
    merged = {"User-Agent": _UA, "Accept-Encoding": "identity"}
    merged.update(headers or {})
    return urlopen(Request(url, headers=merged), timeout=_READ_TIMEOUT)


def _range_total(url):
    """Return the resource length when the server answers range requests."""
    with _http_get(url, {"Range": "bytes=0-0"}) as response:
        status = getattr(response, "status", 200)
        content_range = response.headers.get("Content-Range", "")
    if status == 206 and "/" in content_range:
        total = content_range.rsplit("/", 1)[1].strip()
        if total.isdigit():
            return int(total)
    return 0


def _download_part(url, path, start, end, problems):
    expected = end - start + 1
    last = "not attempted"
    for attempt in range(1, _PART_RETRIES + 1):
        have = os.path.getsize(path) if os.path.exists(path) else 0
        if have == expected:
            return
        if have > expected:
            os.remove(path)
            have = 0
        try:
            headers = {"Range": "bytes=%d-%d" % (start + have, end)}
            with _http_get(url, headers) as response:
                if getattr(response, "status", 200) != 206:
                    raise ConanException(
                        "server ignored range request (HTTP %s)"
                        % getattr(response, "status", 200))
                with open(path, "ab" if have else "wb") as handle:
                    while True:
                        block = response.read(1024 * 1024)
                        if not block:
                            break
                        handle.write(block)
            have = os.path.getsize(path) if os.path.exists(path) else 0
            if have == expected:
                return
            last = "short read %d/%d" % (have, expected)
        except Exception as exc:                       # noqa: BLE001
            last = str(exc)
        time.sleep(min(30, 2 ** attempt))
    problems.append("bytes %d-%d: %s" % (start, end, last))


def _assemble_parts(parts_dir, total, output):
    written = 0
    index = 0
    with open(output, "wb") as out:
        while written < total:
            part = os.path.join(parts_dir, "part-%06d" % index)
            if not os.path.exists(part):
                raise ConanException("missing downloaded chunk: %s" % part)
            with open(part, "rb") as handle:
                shutil.copyfileobj(handle, out, 1024 * 1024)
            written += os.path.getsize(part)
            index += 1


def _download_whole(url, output, problems):
    tmp = output + ".whole"
    for attempt in range(1, _PART_RETRIES + 1):
        try:
            with _http_get(url) as response, open(tmp, "wb") as handle:
                shutil.copyfileobj(response, handle, 1024 * 1024)
            if os.path.getsize(tmp) > 0:
                os.replace(tmp, output)
                return
        except Exception as exc:                       # noqa: BLE001
            problems.append(str(exc))
        time.sleep(min(30, 2 ** attempt))


def _cache_root(conanfile):
    for candidate in (os.environ.get("DOWNLOAD_CACHE"),
                      os.environ.get("CONAN_DOWNLOAD_CACHE"),
                      os.path.expanduser("~/.cache/fpc-sources")):
        if not candidate:
            continue
        try:
            os.makedirs(candidate, exist_ok=True)
            return candidate
        except OSError as exc:
            conanfile.output.warning("fpc: cache dir unusable (%s): %s"
                                     % (candidate, exc))
    return conanfile.source_folder


def _link_or_copy(src, dst):
    if os.path.exists(dst):
        try:
            if os.path.samefile(src, dst):
                return
        except OSError:
            pass
        os.remove(dst)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copyfile(src, dst)


def _download_archive(conanfile, urls, sha256, native):
    root = os.path.dirname(os.path.dirname(native))
    parts_dir = os.path.join(root, "parts", sha256)
    os.makedirs(parts_dir, exist_ok=True)
    errors = []
    for url in urls:
        try:
            total = 0
            try:
                total = _range_total(url)
            except Exception as exc:                   # noqa: BLE001
                conanfile.output.warning("fpc: range probe failed: %s" % exc)
            assembled = os.path.join(parts_dir, "assembled")
            if total > _PART_MIN:
                count = max(1, min(_PART_COUNT,
                                   (total + _PART_MIN - 1) // _PART_MIN))
                span = (total + count - 1) // count
                conanfile.output.info(
                    "fpc: %d parallel chunks over %d MB"
                    % (count, total // (1024 * 1024)))
                problems = []
                threads = []
                for index in range(count):
                    start = index * span
                    end = min(total, start + span) - 1
                    if start >= total:
                        break
                    thread = threading.Thread(
                        target=_download_part,
                        args=(url, os.path.join(parts_dir,
                                                "part-%06d" % index),
                              start, end, problems))
                    thread.start()
                    threads.append(thread)
                for thread in threads:
                    thread.join()
                if problems:
                    raise ConanException(" | ".join(problems))
                _assemble_parts(parts_dir, total, assembled)
            else:
                problems = []
                _download_whole(url, assembled, problems)
                if not os.path.exists(assembled):
                    raise ConanException(" | ".join(problems) or "download failed")
            actual = _sha256_file(assembled)
            if actual != sha256:
                raise ConanException("sha256 mismatch: expected %s, got %s"
                                     % (sha256, actual))
            os.makedirs(os.path.dirname(native), exist_ok=True)
            os.replace(assembled, native)
            conanfile.output.info("fpc: cached %s (from %s)" % (native, url))
            shutil.rmtree(parts_dir, ignore_errors=True)
            return
        except Exception as exc:                       # noqa: BLE001
            errors.append("%s: %s" % (url, exc))
            conanfile.output.warning("fpc: source URL failed: %s" % exc)
    raise ConanException("fpc: could not download %s: %s"
                         % (sha256, " | ".join(errors)))


def fetch_archive(conanfile, urls, sha256, filename):
    """Return a local archive path, downloading it into the shared cache once.

    The file is stored both at Conan content-addressed cache path
    (``<cache>/s/<sha256>``) and under its real filename: tools.files.get()
    chooses its decompressor from the file extension, so it needs the name.
    """
    root = _cache_root(conanfile)
    native = os.path.join(root, "s", sha256)
    named = os.path.join(root, filename)
    if _archive_ok(native, sha256):
        conanfile.output.info("fpc: source cache hit %s" % native)
    else:
        _download_archive(conanfile, urls, sha256, native)
    _link_or_copy(native, named)
    return named


class FpcConan(ConanFile):
    name = "fpc"
    version = "3.2.2"
    package_type = "application"

    license = ("GPL-2.0-or-later WITH GCC-exception-3.1 AND "
               "LGPL-2.1-or-later WITH GCC-exception-3.1")
    author = "OpenHarmonyPCDeveloper"
    url = "https://www.freepascal.org/"
    homepage = "https://www.freepascal.org/"
    description = ("Free Pascal Compiler 3.2.2 (aarch64-linux target) for "
                   "HarmonyOS PC, assembled from the official upstream release")

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration(
                "fpc/3.2.2 currently ships the official aarch64-linux release only")
        if str(self.settings.os) not in ("OHOS", "Linux"):
            raise ConanInvalidConfiguration(
                "fpc/3.2.2 is supported on OHOS/Linux only")

    def _fetch(self, key, filename):
        data = self.conan_data[key]
        urls = data["url"] if isinstance(data["url"], list) else [data["url"]]
        return fetch_archive(self, urls, data["sha256"], filename)

    def source(self):
        # Upstream compiler sources, kept as the FPCDIR source tree for
        # downstream consumers (lazarus requires a directory with rtl/).
        archive = self._fetch("sources", "fpc-3.2.2.source.tar.gz")
        get(self, url="file://" + archive,
            sha256=self.conan_data["sources"]["sha256"],
            destination=self.source_folder, strip_root=True,
            keep_permissions=True)

    def build(self):
        apply_conandata_patches(self)
        dist_dir = os.path.join(self.build_folder, "dist")
        archive = self._fetch("distribution", "fpc-3.2.2.aarch64-linux.tar")
        get(self, url="file://" + archive,
            sha256=self.conan_data["distribution"]["sha256"],
            destination=dist_dir, strip_root=True, keep_permissions=True)

        binary_tar = os.path.join(dist_dir, "binary." + _TARGET + ".tar")
        with tarfile.open(binary_tar) as tar:
            tar.extractall(dist_dir)

        install_dir = os.path.join(self.build_folder, "install")
        os.makedirs(install_dir, exist_ok=True)

        members = os.listdir(dist_dir)
        ordered = []
        # base carries the compiler and the RTL; unit packs follow; utils last.
        for prefix in ("base.", "units-", "utils"):
            picked = sorted(m for m in members
                            if m.startswith(prefix) and m.endswith(".tar.gz"))
            ordered.extend(picked)
        for member in ordered:
            with tarfile.open(os.path.join(dist_dir, member)) as tar:
                tar.extractall(install_dir)

    def _host_cc(self):
        try:
            execs = self.conf.get("tools.build:compiler_executables")
            if isinstance(execs, str):
                execs = json.loads(execs)
            if isinstance(execs, dict):
                return execs.get("c") or execs.get("cpp") or ""
        except Exception:
            pass
        return ""

    def _write_shims(self):
        tooldir = os.path.join(self.package_folder, "libexec", "fpc-toolchain")
        os.makedirs(tooldir, exist_ok=True)
        cc = self._host_cc()
        ccdir = os.path.dirname(cc) if cc else ""
        for name, template in (("as", _AS_SHIM), ("ld", _LD_SHIM)):
            body = template.replace("@CCDIR@", ccdir).replace("@CC@", cc)
            path = os.path.join(tooldir, name)
            save(self, path, body)
            os.chmod(path, 0o755)

    def package(self):
        install_dir = os.path.join(self.build_folder, "install")
        copy(self, "*", install_dir, self.package_folder)

        # Upstream source subset for FPCDIR consumers.
        src_dst = os.path.join(self.package_folder, "share", "fpc-3.2.2-src")
        copy(self, "*", os.path.join(self.source_folder, "rtl"),
             os.path.join(src_dst, "rtl"))
        copy(self, "Makefile*", self.source_folder, src_dst)
        copy(self, "fpmake*", self.source_folder, src_dst)

        bindir = os.path.join(self.package_folder, "bin")
        driver = os.path.join(bindir, "fpc")
        if os.path.isfile(driver):
            os.replace(driver, os.path.join(bindir, "fpc-driver"))

        launcher = (_LAUNCHER
                    .replace("@FPCVER@", self.version)
                    .replace("@TARGET@", _TARGET))
        save(self, os.path.join(bindir, "fpc"), launcher)
        os.chmod(os.path.join(bindir, "fpc"), 0o755)

        self._write_shims()

        # Keep the packaged compilers/tools executable.
        for name in os.listdir(bindir):
            path = os.path.join(bindir, name)
            if os.path.isfile(path):
                os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        compiler = os.path.join(self.package_folder, "lib", "fpc",
                                self.version, "ppca64")
        if os.path.isfile(compiler):
            os.chmod(compiler, os.stat(compiler).st_mode | stat.S_IXUSR)

        self._sign_elf()

    def _sign_elf(self):
        """Re-sign packaged ELF binaries for OHOS.

        OHOS refuses to execute an unsigned/relocated ELF with "Permission
        denied" (E077B).  Strip the old .codesign section and re-sign every
        packaged executable with the on-device binary-sign-tool.  On a
        non-OHOS host (local W3) the tool is absent, so this is a no-op.
        """
        hnp = "/data/service/hnp/bin"
        objcopy = os.path.join(hnp, "llvm-objcopy")
        signer = os.path.join(hnp, "binary-sign-tool")
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool/llvm-objcopy 不可用，跳过 ELF 重签（非 OHOS 主机）")
            return
        targets = []
        bindir = os.path.join(self.package_folder, "bin")
        for root, _dirs, files in os.walk(bindir):
            targets.extend(os.path.join(root, name) for name in files)
        targets.append(os.path.join(self.package_folder, "lib", "fpc",
                                    self.version, "ppca64"))
        for path in sorted(set(targets)):
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "rb") as handle:
                    if handle.read(4) != b"\x7fELF":
                        continue
            except OSError:
                continue
            self.run('"%s" --remove-section .codesign "%s" 2>/dev/null || true'
                     % (objcopy, path))
            self.run('"%s" sign -inFile "%s" -outFile "%s.signed" -selfSign 1'
                     % (signer, path, path))
            if os.path.isfile(path + ".signed"):
                os.replace(path + ".signed", path)
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        fpcdir = os.path.join(self.package_folder, "share", "fpc-3.2.2-src")
        self.buildenv_info.define_path("FPCDIR", fpcdir)
        self.buildenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.define_path("FPCDIR", fpcdir)
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
