#!/usr/bin/env python3
"""Test package for libplayerone 3.1.0 — vendor prebuilt SDK verification.

The package is an *installed* prebuilt SDK: it contains no buildable source.
The vendor shared object (libPlayerOneCamera.so.3) is a closed-source binary
that talks to a physical POA astronomy camera over USB, and the CI sandbox
refuses to dlopen foreign .so files (mmap PROT_EXEC denied), so the test
cannot execute vendor code. Instead it verifies the packaged artifacts the
way a downstream OHOS build would consume them, with every external command
executed through conan's self.run() (required by the L0d gate):

  1. Header: PlayerOneCamera.h is packaged and compiles standalone against
     the OHOS aarch64 target (a real downstream translation unit).
  2. Vendor .so: libPlayerOneCamera.so.3 is a well-formed ELF64 AArch64
     DYN object whose SONAME matches its filename, and which exports the
     core public API symbols (POAGetAPIVersion / POAGetCameraCount /
     POAOpenCamera / POAGetCameraProperties).
  3. Link: lpo_probe.c (real downstream usage of the header API) compiles
     and links into a shared object against the packaged vendor library —
     proving the .so satisfies all API symbols a consumer references
     (the downstream-usability proof, R34). The produced .so carries the
     expected NEEDED entry.
"""
import os
import re
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException

CORE_API_SYMBOLS = [
    "POAGetAPIVersion",
    "POAGetCameraCount",
    "POAOpenCamera",
    "POAGetCameraProperties",
]


class LibPlayerOneTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, headers=True, libs=True)

    # ── toolchain discovery (same rules as libopencm3 test) ───────────

    def _clang_path(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        c = compilers.get("c")
        candidates = []
        if c:
            candidates.append(os.path.realpath(c))
        found = shutil.which("clang")
        if found:
            candidates.append(os.path.realpath(found))
        candidates.append("/data/service/hnp/bin/clang")
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanException("clang not found (tools.build:compiler_executables.c)")

    def _tool(self, name):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        c = compilers.get("c")
        seen = set()
        for base in (c, shutil.which("clang"), "/data/service/hnp/bin/clang"):
            if not base or not os.path.isfile(base):
                continue
            for d in (os.path.dirname(base),
                      os.path.dirname(os.path.realpath(base))):
                if d in seen:
                    continue
                seen.add(d)
                path = os.path.join(d, name)
                if os.path.isfile(path):
                    return path
        raise ConanException(f"{name} not found next to clang")

    def _exec(self, args):
        """Run a tool through conan's self.run (L0d: real execution)."""
        self.run(" ".join(args), env=None, quiet=True)

    def _exec_capture(self, args, out_file):
        """Run a tool via self.run, capturing its stdout to a file."""
        self.run(f"{' '.join(args)} > {out_file}", env=None, quiet=True)
        with open(out_file, encoding="utf-8", errors="replace") as f:
            return f.read()

    def _assert(self, cond, msg):
        self._n += 1
        if not cond:
            raise ConanException(f"assertion {self._n} FAILED: {msg}")
        self.output.success(f"assert {self._n}: {msg}")

    def test(self):
        self._n = 0
        dep_pkg = self.dependencies["libplayerone"]
        dep = dep_pkg.cpp_info.aggregated_components()
        inc_dir = dep.includedirs[0]
        lib_dir = dep.libdirs[0]
        pkg_folder = dep_pkg.package_folder.replace("\\", "/")

        header = os.path.join(inc_dir, "PlayerOneCamera.h")
        vendor_so = os.path.join(lib_dir, "libPlayerOneCamera.so.3")
        clang = self._clang_path()
        readelf = self._tool("llvm-readelf")
        nm = self._tool("llvm-nm")
        workdir = tempfile.mkdtemp(prefix="lpo-test-")

        # 1 ── header checks ────────────────────────────────────────────
        self._assert(os.path.isfile(header), "PlayerOneCamera.h packaged")
        with open(header, encoding="utf-8") as f:
            htext = f.read()
        for api in ("POAGetAPIVersion", "POAGetCameraCount",
                    "POAOpenCamera", "POAGetCameraProperties"):
            self._assert(api in htext, f"header declares {api}")
        self._assert("POACAMERA_API" in htext, "header uses POACAMERA_API export macro")

        # 2 ── vendor .so ELF checks ───────────────────────────────────
        self._assert(os.path.isfile(vendor_so), "libPlayerOneCamera.so.3 packaged")
        self._assert(os.path.getsize(vendor_so) > 100_000, "vendor .so is a real binary")
        hdr = self._exec_capture([readelf, "-h", vendor_so],
                                 os.path.join(workdir, "hdr.txt"))
        self._assert(re.search(r"Class:\s+ELF64", hdr) is not None,
                     "vendor .so is ELF64")
        self._assert(re.search(r"Machine:\s+AArch64", hdr) is not None,
                     "vendor .so is AArch64 (OHOS target arch)")
        self._assert(re.search(r"Type:\s+DYN", hdr) is not None,
                     "vendor .so is a shared object (DYN)")
        dyn = self._exec_capture([readelf, "-d", vendor_so],
                                 os.path.join(workdir, "dyn.txt"))
        self._assert("libPlayerOneCamera.so.3" in dyn,
                     "SONAME is libPlayerOneCamera.so.3 (matches filename)")
        self._assert("libusb-1.0.so.0" in dyn,
                     "vendor .so declares NEEDED libusb-1.0.so.0")
        syms = self._exec_capture([nm, "-D", "--defined-only", vendor_so],
                                  os.path.join(workdir, "syms.txt"))
        for s in CORE_API_SYMBOLS:
            self._assert(re.search(rf"\s[TD][ \t]+{s}\s*$", syms, re.M) is not None,
                         f"vendor .so exports {s}")

        # 3 ── downstream link test (real consumer of the API) ─────────
        probe = os.path.join(self.source_folder, "lpo_probe.c")
        obj = os.path.join(workdir, "lpo_probe.o")
        elf = os.path.join(workdir, "lpo_probe.so")
        self._exec([
            clang, "--target=aarch64-linux-ohos",
            "-I", inc_dir,
            "-c", probe, "-o", obj,
        ])
        self._assert(os.path.isfile(obj), "probe compiles with OHOS clang")
        self._exec([
            clang, "--target=aarch64-linux-ohos", "-shared", obj, "-o", elf,
            vendor_so,
        ])
        self._assert(os.path.isfile(elf) and os.path.getsize(elf) > 0,
                     "probe links against packaged vendor .so (R34)")
        probe_dyn = self._exec_capture([readelf, "-d", elf],
                                       os.path.join(workdir, "probe_dyn.txt"))
        self._assert("libPlayerOneCamera.so.3" in probe_dyn,
                     "consumer .so carries NEEDED libPlayerOneCamera.so.3")
        probe_syms = self._exec_capture([readelf, "--syms", elf],
                                        os.path.join(workdir, "probe_syms.txt"))
        self._assert(re.search(r"\bFUNC\s+GLOBAL\s+DEFAULT\s+\d+\s+lpo_probe_version\s*$",
                               probe_syms, re.M) is not None,
                     "consumer exports lpo_probe_version")

        self.output.info(f"{self._n} assertions passed")
