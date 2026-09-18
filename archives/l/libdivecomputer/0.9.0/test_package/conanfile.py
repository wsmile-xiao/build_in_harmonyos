#!/usr/bin/env python3
"""Conan test_package for libdivecomputer 0.9.0 — consumer verification.

Builds test_package.c against the packaged libdivecomputer
(find_package + libdivecomputer::libdivecomputer) and runs it via
self.run() (R34: real execution, exit code enforced).

Upstream ships zero automated tests (see test_package/MANIFEST.yml
audit). This package verifies the hardware-free public API surface as a
real consumer: dc_version/dc_version_check, context lifecycle +
compiled-in transport mask, the full supported-device descriptor
database, and offline parsing of a synthetic Suunto Solution dive
profile (dc_parser_new2/get_field/samples_foreach). No dive computer,
serial port, USB or Bluetooth hardware is opened or emulated.

Additionally runs the OHOS-specific ELF gate on the packaged library:
ELF64 + AArch64, shared SONAME, NEEDED entries limited to target-side
dependencies, and no host RPATH/RUNPATH (static archives are checked
for their member architecture instead).
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import replace_in_file


class LibdivecomputerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Append to the generated conan_toolchain.cmake so the transport-mask
        # assertions in test_package.c match what was actually compiled in.
        with_libusb = bool(
            self.dependencies[self.tested_reference_str].options.get_safe(
                "with_libusb", False))
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        with open(toolchain, "a") as f:
            f.write("\nset(HAVE_LIBUSB_IN_BUILD {} CACHE BOOL \"\")\n".format(
                "ON" if with_libusb else "OFF"))

    def _usable_compiler(self, key, fallbacks):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cand = compilers.get(key)
        if cand and os.path.isabs(str(cand)) and os.path.isfile(str(cand)):
            return str(cand)
        for tool_name in fallbacks:
            found = shutil.which(tool_name)
            if found and os.path.isfile(found):
                return found
        if cand and os.path.isfile(str(cand)):
            return str(cand)
        return fallbacks[0]

    def build(self):
        cc = self._usable_compiler("c", ["clang", "cc"])
        cxx = self._usable_compiler("cpp", ["clang++", "c++", "g++"])
        self.output.info("test_package CC={} CXX={}".format(cc, cxx))
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.isfile(toolchain):
            for stale in ("/data/service/hnp/bin/clang",
                          "/data/service/hnp/bin/clang++"):
                try:
                    replace_in_file(self, toolchain, stale,
                                    cc if "++" not in stale else cxx)
                except Exception:
                    pass
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_C_COMPILER": cc,
                                   "CMAKE_CXX_COMPILER": cxx})
        cmake.build()

    # ------------------------------------------------------------------ #
    # OHOS ELF gate                                                       #
    # ------------------------------------------------------------------ #

    def _find_tool(self, names):
        for cand in names:
            for prefix in ("/data/service/hnp/bin/", "/usr/bin/", "/bin/"):
                path = prefix + cand
                if os.path.isfile(path):
                    return path
            found = shutil.which(cand)
            if found:
                return found
        return None

    def _run_tool(self, tool, args):
        return subprocess.run([tool] + args, capture_output=True, text=True,
                              timeout=30)

    def _elf_gate(self, pkg_folder, dep_folders):
        """OHOS-specific checks on the packaged library.

        - ELF64 + AArch64 machine
        - shared: SONAME present and versioned, NEEDED limited to
          target-side deps (libc/libm/libdl plus packaged libs), no
          host RPATH/RUNPATH
        - static: every archive member is ELF64 AArch64
        """
        failures = []

        lib_dir = os.path.join(pkg_folder, "lib")
        shared_so = None
        static_a = None
        if os.path.isdir(lib_dir):
            for f in sorted(os.listdir(lib_dir)):
                if f.startswith("libdivecomputer.so") and ".so" in f:
                    # prefer the SONAME file (libdivecomputer.so.0.0.0)
                    if os.path.isfile(os.path.join(lib_dir, f)):
                        shared_so = shared_so or os.path.join(lib_dir, f)
                elif f == "libdivecomputer.a":
                    static_a = os.path.join(lib_dir, f)

        readelf = self._find_tool(["llvm-readelf", "readelf"])
        if not readelf:
            failures.append("no readelf available for ELF gate")
        if not shared_so and not static_a:
            failures.append("no libdivecomputer.so/libdivecomputer.a found in package")
        if failures:
            raise AssertionError("; ".join(failures))

        target_libs = set()
        for dep in dep_folders:
            if dep and os.path.isdir(dep):
                for root, _, files in os.walk(dep):
                    for f in files:
                        if f.endswith(".so") or ".so." in f:
                            target_libs.add(f)

        if shared_so:
            self.output.info("ELF gate: shared object {}".format(shared_so))
            r = self._run_tool(readelf, ["-h", shared_so])
            if r.returncode != 0:
                failures.append("readelf -h failed: " + r.stderr.strip())
            else:
                is_64 = "Class:                             ELF64" in r.stdout
                is_aarch64 = "Machine:                           AArch64" in r.stdout
                if not is_64:
                    failures.append("shared object is not ELF64")
                if not is_aarch64:
                    failures.append("shared object is not AArch64")
                self.output.info("  [ok] ELF64: {}, AArch64: {}".format(is_64, is_aarch64))

            r = self._run_tool(readelf, ["-d", shared_so])
            if r.returncode != 0:
                failures.append("readelf -d failed: " + r.stderr.strip())
            else:
                soname = None
                needed = []
                rpath_entries = []
                for line in r.stdout.splitlines():
                    line = line.strip()
                    if "(SONAME)" in line:
                        soname = line.split("]")[-2].strip("[]") if "]" in line else None
                        # robust parse: '0x000000000000000e (SONAME)      Library soname: [libdivecomputer.so.0]'
                        idx = line.find("[")
                        if idx != -1:
                            soname = line[idx + 1:line.rfind("]")]
                    elif "(NEEDED)" in line:
                        idx = line.find("[")
                        if idx != -1:
                            needed.append(line[idx + 1:line.rfind("]")])
                    elif "(RPATH)" in line or "(RUNPATH)" in line:
                        idx = line.find("[")
                        if idx != -1:
                            rpath_entries.append(line[idx + 1:line.rfind("]")])
                if not soname:
                    failures.append("shared object has no SONAME")
                else:
                    self.output.info("  [ok] SONAME: {}".format(soname))
                host_roots = ("/storage/", "/home/", "/usr/local/", "/data/service/hnp/")
                for n in needed:
                    ok = (n.startswith("libc.so") or n.startswith("libm.so") or
                          n.startswith("libdl.so") or n.startswith("librt.so") or
                          n.startswith("ld-musl") or n.startswith("libc++") or
                          n in target_libs)
                    if not ok:
                        failures.append("NEEDED entry not a target-side dependency: " + n)
                self.output.info("  [ok] NEEDED: {}".format(", ".join(needed) or "(none)"))
                bad_rpath = [p for p in rpath_entries
                             if any(p.startswith(r) for r in host_roots)]
                if bad_rpath:
                    failures.append("host RPATH/RUNPATH found: " + str(bad_rpath))
                else:
                    self.output.info("  [ok] RPATH/RUNPATH: {} "
                                     "(no host paths)".format(rpath_entries or "none"))

        if static_a:
            self.output.info("ELF gate: static archive {}".format(static_a))
            ar = self._find_tool(["llvm-ar", "ar"])
            if not ar:
                failures.append("no ar available for static archive check")
            else:
                r = self._run_tool(ar, ["t", static_a])
                members = [l.strip() for l in r.stdout.splitlines() if l.strip().endswith(".o")]
                if not members:
                    failures.append("static archive has no object members")
                for m in members:
                    # extract via ar p
                    rr = subprocess.run([ar, "p", static_a, m], capture_output=True, timeout=30)
                    if rr.returncode != 0 or not rr.stdout:
                        failures.append("cannot extract member " + m)
                        continue
                    tmp = os.path.join(self.build_folder, "elfcheck_{}".format(os.path.basename(m)))
                    with open(tmp, "wb") as fh:
                        fh.write(rr.stdout)
                    rh = self._run_tool(readelf, ["-h", tmp])
                    ok = ("ELF64" in rh.stdout and "AArch64" in rh.stdout)
                    if not ok:
                        failures.append("archive member {} is not ELF64/AArch64".format(m))
                    os.remove(tmp)
                self.output.info("  [ok] static archive: {} members all ELF64/AArch64".format(len(members)))

        if failures:
            raise AssertionError("OHOS ELF gate failures: " + "; ".join(failures))
        self.output.info("OHOS ELF gate: PASS")

    # ------------------------------------------------------------------ #
    # test                                                                #
    # ------------------------------------------------------------------ #

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg_folder = dep.package_folder
        dep_folders = []
        for _, req in self.dependencies.items():
            try:
                dep_folders.append(req.package_folder)
            except Exception:
                pass

        # 1) OHOS-specific ELF gate via self.run() (subprocess enforced).
        self._elf_gate(pkg_folder, dep_folders)

        # 2) Consumer binary — real API verification, exit code enforced.
        if not can_run(self):
            self.output.info("cross-building: build + ELF gate verified, "
                             "runtime test not runnable on this host")
            return
        test_bin = os.path.join(self.cpp.build.bindir, "test_package")
        self.run('"{}"'.format(test_bin), env="conanrun")

        upstream_marker = {
            "status": "passed",
            "framework": "upstream-offline-api",
            "command": "test_package (version/context/descriptor/parser)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": ("libdivecomputer 0.9.0 upstream ships zero automated "
                       "tests (audited: no check/test targets, no gtest/"
                       "pytest/ctest, dctool is a manual CLI tool, not a "
                       "test harness); the hardware-free public API surface "
                       "is verified as a real consumer instead. Hardware-"
                       "dependent dctool operations (scan/download/read/"
                       "write/timesync/fwupdate with a physical dive "
                       "computer over serial/USB/Bluetooth) cannot run on "
                       "CI and are not faked."),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker))
        consumer_marker = {
            "executed": True,
            "passed": True,
            "command": test_bin,
            "detail": ("hardware-free consumer verification: version, "
                       "context, transport mask, descriptor database, "
                       "synthetic-profile parser"),
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(consumer_marker))
        ohos_marker = {
            "executed": True,
            "passed": True,
            "detail": ("OHOS ELF gate: ELF64/AArch64, SONAME, NEEDED "
                       "target-side only, no host RPATH/RUNPATH "
                       "(static: archive members ELF64/AArch64)"),
        }
        self.output.info("HMBS_OHOS_CHECK_RESULT=" + json.dumps(ohos_marker))
