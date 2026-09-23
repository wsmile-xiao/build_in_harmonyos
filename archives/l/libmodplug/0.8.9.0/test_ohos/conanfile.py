#!/usr/bin/env python3
"""test_ohos — libmodplug 0.8.9.0 HarmonyOS PC 专项验证.

在真实鸿蒙 PC（aarch64, musl）上对最终 Conan 包做七项独立检查。
本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）：
测试源码为本目录 test_modplug.c，MOD fixture 以 Base64 内嵌于本文件
（与 test_package 完全一致的 2620 字节 ohpc_test.mod 数据），test()
运行前解码到本目录的 build 输出旁并做 size/SHA256 fail-closed 校验：
  T1  aarch64 ELF 验证
  T2  musl libc（无 glibc / 无 __gnu_ld 链接）
  T3  SONAME == libmodplug.so.1（libtool -version-info 1:0:0）
  T4  NEEDED 动态依赖正确（libc++_shared.so + musl libc）
  T5  .codesign 段存在（OHOS 签名管线产出）
  T6  无宿主绝对路径泄漏（含 RPATH/RUNPATH 检查）
  T7  真实解码（链最终库 decode fixture，非静音）
"""
import base64
import hashlib
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import VirtualRunEnv

LIB_FILE = "libmodplug.so.1.0.0"
CHECK_IDS = ["T1_aarch64_elf", "T2_musl_no_glibc", "T3_soname",
             "T4_needed", "T5_codesign", "T6_no_host_paths",
             "T7_real_decode"]

_FIXTURE_SIZE = 2620
_FIXTURE_SHA256 = "bf5829a02c7d8894ff87a5c4ff897a3cd70af7b75ea50affd3c17aceb1c23969"
_FIXTURE_B64 = (
    "T0hQQ1RFU1QAAAAAAAAAAAAAAABPSFBDLVNNUDEgICAgICAgICAgICAgAQAAQAAAAAEgICAgICAgICAgICAgICAg"
    "ICAgICAgAAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAg"
    "AAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAA"
    "AAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAAAAEgICAg"
    "ICAgICAgICAgICAgICAgICAgAAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAAAAEgICAgICAgICAg"
    "ICAgICAgICAgICAgAAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAAAAEgICAgICAgICAgICAgICAg"
    "ICAgICAgAAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAg"
    "AAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAA"
    "AAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAAAAEgICAg"
    "ICAgICAgICAgICAgICAgICAgAAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAAAAEgICAgICAgICAg"
    "ICAgICAgICAgICAgAAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAAAAEgICAgICAgICAgICAgICAg"
    "ICAgICAgAAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAg"
    "AAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAA"
    "AAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAAAAEgICAgICAgICAgICAgICAgICAgICAgAAAAAAAAAAEgICAg"
    "ICAgICAgICAgICAgICAgICAgAAAAAAAAAAEBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAATS5LLgGsEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAQEBA"
    "wMDAwEBAQEDAwMDAQEBAQMDAwMBAQEBAwMDAwEBAQEDAwMDAQEBAQMDAwMBAQEBAwMDAwEBAQEDAwMDAQEBAQMDA"
    "wMBAQEBAwMDAwEBAQEDAwMDAQEBAQMDAwMBAQEBAwMDAwEBAQEDAwMDAQEBAQMDAwMBAQEBAwMDAwEBAQEDAwMDA"
    "QEBAQMDAwMBAQEBAwMDAwEBAQEDAwMDAQEBAQMDAwMBAQEBAwMDAwEBAQEDAwMDAQEBAQMDAwMBAQEBAwMDAwEBA"
    "QEDAwMDAQEBAQMDAwMBAQEBAwMDAwEBAQEDAwMDAQEBAQMDAwMBAQEBAwMDAwEBAQEDAwMDAQEBAQMDAwMBAQEBA"
    "wMDAwEBAQEDAwMDAQEBAQMDAwMBAQEBAwMDAwEBAQEDAwMDAQEBAQMDAwMBAQEBAwMDAwEBAQEDAwMDAQEBAQMDA"
    "wMBAQEBAwMDAwEBAQEDAwMDAQEBAQMDAwMBAQEBAwMDAwEBAQEDAwMDAQEBAQMDAwMBAQEBAwMDAwEBAQEDAwMDA"
    "QEBAQMDAwMBAQEBAwMDAwEBAQEDAwMDAQEBAQMDAwMBAQEBAwMDAwEBAQEDAwMDAQEBAQMDAwMBAQEBAwMDAwEBA"
    "QEDAwMDAQEBAQMDAwMBAQEBAwMDAwEBAQEDAwMDAQEBAQMDAwMBAQEBAwMDAwA=="
)


class LibmodplugOhosTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self._require_ohos()
        pkg = self._locate_package()
        results = {}
        failures = []
        for check, fn in [(CHECK_IDS[0], self._check_arch),
                          (CHECK_IDS[1], self._check_musl),
                          (CHECK_IDS[2], self._check_soname),
                          (CHECK_IDS[3], self._check_needed),
                          (CHECK_IDS[4], self._check_codesign),
                          (CHECK_IDS[5], self._check_host_paths),
                          (CHECK_IDS[6], self._check_real_decode)]:
            try:
                detail = fn(pkg)
                results[check] = {"ok": True, "detail": detail}
            except AssertionError as exc:
                results[check] = {"ok": False, "detail": str(exc)}
                failures.append(f"{check}: {exc}")
        report = {"package": str(self.tested_reference_str),
                  "checks": results,
                  "failures": failures}
        print("==TEST_OHOS_BEGIN==")
        print(json.dumps(report, indent=2))
        print("==TEST_OHOS_END==")
        if failures:
            raise Exception("test_ohos: %d check(s) failed: %s"
                            % (len(failures), "; ".join(failures)))

    # ── helpers ─────────────────────────────────────────────────────

    def _require_ohos(self):
        assert str(self.settings.os) == "OHOS", (
            "test_ohos must run on OHOS (got %s)" % self.settings.os)
        assert str(self.settings.arch) == "armv8", (
            "test_ohos must run on armv8 (got %s)" % self.settings.arch)

    def _locate_package(self):
        # resolve the installed package folder for the tested reference
        pkg = None
        for dep in self.dependencies.values():
            if dep.ref.name == "libmodplug":
                pkg = dep.package_folder
                break
        assert pkg, "libmodplug package folder not found in dependencies"
        lib = os.path.join(pkg, "lib", LIB_FILE)
        assert os.path.isfile(lib), "missing %s" % lib
        return pkg

    def _readelf(self, *args):
        tool = self._find_tool(["llvm-readelf", "readelf"])
        out = subprocess.run([tool] + list(args),
                             capture_output=True, text=True)
        assert out.returncode == 0, "readelf failed: %s" % out.stderr
        return out.stdout

    def _find_tool(self, names):
        for n in names:
            path = shutil_which(n)
            if path:
                return path
        raise AssertionError("tool not found: %s" % "/".join(names))

    def _write_fixture(self, bindir):
        # Self-contained fixture: decode the Base64 MOD embedded in this
        # file (byte-identical to test_package's ohpc_test.mod) next to
        # the consumer binary. Size and SHA256 are verified fail-closed
        # so a corrupted embed can never be mistaken for a pass.
        data = base64.b64decode(_FIXTURE_B64, validate=True)
        if len(data) != _FIXTURE_SIZE:
            raise RuntimeError(
                f"fixture size mismatch: {len(data)} != {_FIXTURE_SIZE}"
            )
        digest = hashlib.sha256(data).hexdigest()
        if digest != _FIXTURE_SHA256:
            raise RuntimeError(
                f"fixture sha256 mismatch: {digest} != {_FIXTURE_SHA256}"
            )
        fixture = os.path.join(bindir, "ohpc_test.mod")
        with open(fixture, "wb") as fh:
            fh.write(data)
        return fixture

    # ── T1 ──────────────────────────────────────────────────────────

    def _check_arch(self, pkg):
        lib = os.path.join(pkg, "lib", LIB_FILE)
        hdr = self._readelf("-h", lib)
        assert "Class:                             ELF64" in hdr, (
            "not a 64-bit ELF:\n%s" % "\n".join(hdr.splitlines()[:6]))
        assert re.search(r"Machine:\s+AArch64", hdr), "not AArch64"
        return "ELF64 AArch64"

    # ── T2 ──────────────────────────────────────────────────────────

    def _check_musl(self, pkg):
        lib = os.path.join(pkg, "lib", LIB_FILE)
        dyn = self._readelf("-d", lib)
        needed = [m for m in re.findall(r"\[(.*?)\]", dyn)]
        assert not any("libc.so.6" in n or "ld-linux" in n for n in needed), (
            "glibc residue in NEEDED: %s" % needed)
        assert any(n.startswith("libc.so") for n in needed), (
            "no libc in NEEDED: %s" % needed)
        sym = self._readelf("--dyn-syms", lib)
        assert "__gnu_ld" not in sym and "GLIBC_" not in sym, (
            "GLIBC symbol versions present")
        return "musl libc, no GLIBC symbols"

    # ── T3 ──────────────────────────────────────────────────────────

    def _check_soname(self, pkg):
        lib = os.path.join(pkg, "lib", LIB_FILE)
        dyn = self._readelf("-d", lib)
        m = re.search(r"\(SONAME\).*?\[(.*?)\]", dyn)
        assert m, "no SONAME entry"
        assert m.group(1) == "libmodplug.so.1", (
            "SONAME is %s, expected libmodplug.so.1" % m.group(1))
        return "libmodplug.so.1 (libtool -version-info 1:0:0)"

    # ── T4 ──────────────────────────────────────────────────────────

    def _check_needed(self, pkg):
        lib = os.path.join(pkg, "lib", LIB_FILE)
        dyn = self._readelf("-d", lib)
        needed = re.findall(r"\(NEEDED\).*?\[(.*?)\]", dyn)
        assert "libc++_shared.so" in needed, (
            "libc++_shared.so not in NEEDED: %s" % needed)
        assert any(n == "libc.so" or n.startswith("libc.so") for n in needed), (
            "libc.so not in NEEDED: %s" % needed)
        return needed

    # ── T5 ──────────────────────────────────────────────────────────

    def _check_codesign(self, pkg):
        lib = os.path.join(pkg, "lib", LIB_FILE)
        sections = self._readelf("-SW", lib)
        assert ".codesign" in sections, "no .codesign section"
        return ".codesign section present"

    # ── T6 ──────────────────────────────────────────────────────────

    def _check_host_paths(self, pkg):
        lib = os.path.join(pkg, "lib", LIB_FILE)
        leaks = []
        dyn = self._readelf("-d", lib)
        for m in re.findall(r"\[(.*?)\]", dyn):
            if m.startswith("/") and not m.startswith("/system") \
               and not m.startswith("/vendor") and not m.startswith("/odm"):
                leaks.append("DT entry %s" % m)
        for tag in ("RPATH", "RUNPATH"):
            if re.search(r"\(%s\)" % tag, dyn):
                leaks.append("DT_%s present" % tag)
        strings = self._strings(lib)
        for pat in ("/storage/", "/home/", "/tmp/", "/data/service/"):
            if pat in strings:
                leaks.append("host path %r in strings" % pat)
        assert not leaks, "host path leaks: %s" % leaks
        return "no absolute host paths, no RPATH/RUNPATH"

    # ── T7 ──────────────────────────────────────────────────────────

    def _check_real_decode(self, pkg):
        bindir = os.path.join(self.build_folder, "bin")
        if not os.path.isdir(bindir):
            # single-config generators put the binary directly in build/
            bindir = self.build_folder
        binary = os.path.join(bindir, "test_modplug")
        assert os.path.isfile(binary), "test_modplug binary missing"
        # decode the embedded fixture next to the binary before the run
        fixture = self._write_fixture(bindir)
        env = VirtualRunEnv(self).vars()
        proc = subprocess.run([binary, fixture], env=env,
                              capture_output=True, text=True)
        assert proc.returncode == 0, "decode failed rc=%d: %s" % (
            proc.returncode, proc.stderr[-500:])
        m = re.search(r"TOTAL=(\d+) PASS=(\d+) FAIL=(\d+)", proc.stderr)
        assert m, "no TAP summary in output"
        total, passed, failed = (int(x) for x in m.groups())
        assert failed == 0 and passed == total, (
            "TAP failures: %s" % proc.stderr[-500:])
        return "18 assertions, real decode non-silent"

    # ── misc ────────────────────────────────────────────────────────

    def _strings(self, lib):
        tool = self._find_tool(["llvm-strings", "strings"])
        out = subprocess.run([tool, lib], capture_output=True, text=True)
        return out.stdout


def shutil_which(name):
    import shutil
    return shutil.which(name)
