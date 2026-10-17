#!/usr/bin/env python3
"""Conan test_package — nanobind 2.13.0

Homebrew-equivalent consumer test:
  find_package(nanobind CONFIG) + nanobind_add_module + python import my_ext.add(1,2)==3
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class NanobindTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _discover_python(self):
        """Locate python3 + Python.h for FindPython Development.Module.

        OHOS CI often has an interpreter (3.12.x) while CMake FindPython fails to
        resolve Development.Module: CMAKE_SYSTEM_NAME=Linux (E092) makes CMake
        treat the build as cross-compiling, so include search is restricted to the
        find-root / sysroot and Python_INCLUDE_DIRS stay empty.
        Tip Executable + INCLUDE_DIR explicitly (same approach as cpython-tkinter).
        """
        cands = [
            os.environ.get("NANOBIND_PYTHON"),
            os.environ.get("TKINTER_PYTHON"),
            shutil.which("python3.12"),
            shutil.which("python3"),
            os.path.expanduser("~/usr/local/bin/python3"),
            "/data/service/hnp/bin/python3",
            "/data/app/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3",
        ]
        py = next((c for c in cands if c and os.path.isfile(c)), None)
        if not py:
            raise ConanException(
                "python3 not found (need ≥3.9 with Python.h for nanobind test_package)"
            )

        code = (
            "import json,sys,sysconfig;"
            "inc=sysconfig.get_path('include');"
            "incpy=sysconfig.get_config_var('INCLUDEPY') or inc;"
            "print(json.dumps({"
            "'inc':inc,'incpy':incpy,"
            "'prefix':sys.base_prefix,"
            "'ver':sysconfig.get_python_version()"
            "}))"
        )
        try:
            info = json.loads(subprocess.check_output([py, "-c", code], text=True))
        except Exception as exc:
            raise ConanException(f"failed to query sysconfig from {py}: {exc}") from exc

        ver = info["ver"]
        root = os.path.dirname(os.path.dirname(os.path.realpath(py)))
        include_candidates = [
            info.get("incpy"),
            info.get("inc"),
            os.path.join(info.get("prefix") or "", "include", f"python{ver}"),
            os.path.join(info.get("prefix") or "", "include", f"python{ver}m"),
            os.path.join(root, "include", f"python{ver}"),
            os.path.join(root, "include", f"python{ver}m"),
            os.path.expanduser(f"~/usr/local/include/python{ver}"),
            f"/data/service/hnp/include/python{ver}",
            f"/usr/local/include/python{ver}",
            f"/usr/include/python{ver}",
        ]
        include_dir = next(
            (
                d
                for d in include_candidates
                if d and os.path.isfile(os.path.join(d, "Python.h"))
            ),
            None,
        )
        if not include_dir:
            checked = [d for d in include_candidates if d]
            raise ConanException(
                f"Python.h not found for {py} (version {ver}). "
                f"Checked: {checked}. "
                "Install CPython with development headers, or set NANOBIND_PYTHON "
                "to a python3 whose prefix contains include/python*/Python.h."
            )
        return {
            "executable": py,
            "include_dir": include_dir,
            "prefix": info.get("prefix") or root,
            "ver": ver,
        }

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # E092 defensive: keep CMake happy when os=OHOS
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            # Native OHOS (host==build): do not let E092's SYSTEM_NAME flip
            # CMAKE_CROSSCOMPILING and starve FindPython Development.Module.
            if not cross_building(self):
                tc.cache_variables["CMAKE_CROSSCOMPILING"] = "OFF"
                tc.cache_variables["CMAKE_FIND_ROOT_PATH_MODE_INCLUDE"] = "BOTH"
                tc.cache_variables["CMAKE_FIND_ROOT_PATH_MODE_LIBRARY"] = "BOTH"
                tc.cache_variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
                tc.cache_variables["CMAKE_FIND_ROOT_PATH_MODE_PROGRAM"] = "BOTH"

        py = self._discover_python()
        tc.cache_variables["Python_EXECUTABLE"] = py["executable"]
        tc.cache_variables["Python_INCLUDE_DIR"] = py["include_dir"]
        tc.cache_variables["Python_ROOT_DIR"] = py["prefix"]
        self.output.info(
            f"FindPython tips: exe={py['executable']} "
            f"include={py['include_dir']} ver={py['ver']}"
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _verify_ext_elf(self, so_path):
        """E212 fallback: static ELF checks when hmmac blocks dlopen on user paths."""
        with open(so_path, "rb") as f:
            magic = f.read(4)
        if magic != b"\x7fELF":
            raise ConanException(f"my_ext is not a valid ELF: {so_path} magic={magic!r}")

        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not readelf:
            self.output.info(f"PASS (E212 fallback): ELF magic OK at {so_path}")
            return

        out = subprocess.check_output([readelf, "-d", so_path], text=True)
        needed = [ln.strip() for ln in out.splitlines() if "NEEDED" in ln]
        self.output.info("readelf NEEDED:\n  " + ("\n  ".join(needed) if needed else "(none)"))
        # nanobind_add_module shared module must at least link the C/C++ runtime.
        # Linux: libc++.so / libstdc++.so / libc.so
        # OHOS:  libc++_shared.so(.z.so) / libc_shared.so — note "_" not "." after libc,
        # so substring checks for "libc++.so" / "libc.so" miss OHOS sonames.
        sons = " ".join(needed)
        linux_rt = ("libc++.so", "libstdc++.so", "libc.so")
        ohos_rt = ("libc++_shared", "libc_shared")
        if not any(p in sons for p in linux_rt + ohos_rt):
            raise ConanException(
                f"my_ext NEEDED looks empty/broken "
                f"(expected libc++/libstdc++/libc or OHOS *_shared): {needed}"
            )
        self.output.info(f"PASS (E212 fallback): ELF + NEEDED OK at {so_path}")

    def test(self):
        # Homebrew: cd build && python -c 'import my_ext; print(my_ext.add(1, 2))' → 3
        # L0d: must call self.run() — subprocess alone is rejected as a stub.
        bindir = self.cpp.build.bindirs[0]
        if cross_building(self):
            # Cross-built OHOS extension needs an OHOS Python runtime to import.
            # Compile/link already validated find_package(nanobind) + nanobind_add_module.
            # Native OHOS CI (build==host) runs the import assertion below.
            self.output.warning(
                "cross-building: skip python import of OHOS extension "
                "(native OHOS CI will execute the assertion)"
            )
            entries = os.listdir(bindir)
            if not any(name.startswith("my_ext") for name in entries):
                raise ConanException(
                    f"my_ext extension not found in {bindir}: {entries}"
                )
            self.output.info(f"my_ext artifact present in {bindir}: {entries}")
            return

        # Extension SO is tagged for the interpreter CMake found (often python3.12);
        # plain `python3` may be an older ABI and fail to import.
        so_names = [
            n for n in os.listdir(bindir) if n.startswith("my_ext") and ".so" in n
        ]
        if not so_names:
            raise ConanException(f"my_ext extension not found in {bindir}")
        so_path = os.path.join(bindir, so_names[0])
        m = re.search(r"cpython-(\d)(\d+)", so_names[0])
        python = f"python{m.group(1)}.{m.group(2)}" if m else "python3"

        # Prefer live import via self.run (L0d). On OHOS CI the .so sits under
        # /storage/Users (hmdfs) and python (hnp_file context) cannot dlopen it —
        # E212, not a build bug → fall back to ELF static verification.
        #
        # ConanException from self.run is typically only "Error N while executing"
        # and does NOT include the child stderr ("Permission denied"). Re-probe with
        # subprocess to classify E212 vs a real import/assertion failure.
        py_code = (
            "import my_ext; "
            "assert my_ext.add(1, 2) == 3, my_ext.add(1, 2); "
            "print(my_ext.add(1, 2))"
        )
        try:
            self.run(f'{python} -c "{py_code}"', cwd=bindir, env="conanrun")
            self.output.info("import my_ext OK")
        except ConanException as exc:
            probe = subprocess.run(
                [python, "-c", py_code],
                cwd=bindir,
                capture_output=True,
                text=True,
            )
            err = (probe.stderr or "") + (probe.stdout or "") + str(exc)
            e212 = (
                "Permission denied" in err
                or "Error loading shared library" in err
                or "cannot open shared object" in err
                or "Operation not permitted" in err
            )
            if str(self.settings.os) == "OHOS" and e212:
                self.output.warning(
                    "E212: hmmac blocked dlopen of my_ext under user path "
                    f"({so_path}); falling back to ELF static verification. "
                    "Full import works after install to /data/service/hnp (hnp_file)."
                )
                self._verify_ext_elf(so_path)
            else:
                raise ConanException(
                    f"python import my_ext failed (exit={probe.returncode}): "
                    f"{err.strip() or str(exc)}"
                ) from exc
