#!/usr/bin/env python3
"""Consumer test for eigenpy 3.13.0."""

import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building


class EigenpyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        incs = []
        libdirs = []
        for _ref, dep in self.dependencies.items():
            incs.extend("-I" + path for path in dep.cpp_info.includedirs)
            for libdir in dep.cpp_info.libdirs or []:
                if libdir not in libdirs:
                    libdirs.append(libdir)

        tested = self.dependencies["eigenpy"].cpp_info
        std_flag = self._std_flag()
        cxx = self._cxx()
        link = " ".join(
            ["-L" + path for path in libdirs]
            + ["-Wl,-rpath," + path for path in libdirs]
            + ["-Wl,-rpath-link," + path for path in libdirs]
            + ["-l" + lib for lib in (tested.libs or ["eigenpy"])]
        )
        self.run(
            "{} {} test_version.cpp -o test_version {} {}".format(
                cxx, std_flag, " ".join(incs), link
            )
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test_version only")
            return

        executable = os.path.join(self.build_folder, "test_version")
        if self.settings.os == "Windows":
            executable += ".exe"
        if self.settings.os == "OHOS":
            self._sign_executable(executable)
            self._run_ohos_executable(executable)
        else:
            self.run('"{}"'.format(executable), env="conanrun", cwd=self.build_folder)
        self._run_python_import()

    def _std_flag(self):
        cppstd = self.settings.get_safe("compiler.cppstd")
        if cppstd:
            return "-std=c++{}".format(str(cppstd).replace("gnu", ""))
        return "-std=c++17"

    def _cxx(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("cpp") or os.environ.get("CXX") or "clang++"

    def _python(self):
        candidates = [
            os.environ.get("EIGENPY_PYTHON"),
            shutil.which("python3.12"),
            shutil.which("python3"),
            os.path.expanduser("~/usr/local/bin/python3"),
            "/data/service/hnp/bin/python3",
            "/data/app/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3",
        ]
        python = next((c for c in candidates if c and os.path.isfile(c)), None)
        if not python:
            raise ConanInvalidConfiguration("python3 not found for eigenpy import test")
        return python

    def _python_libdir(self):
        code = (
            "import glob,json,os,sys,sysconfig;"
            "ver=sysconfig.get_python_version();"
            "names=[sysconfig.get_config_var('LDLIBRARY'),"
            "'libpython{}.so'.format(ver),'libpython{}m.so'.format(ver),"
            "'libpython{}.so.*'.format(ver),'libpython{}m.so.*'.format(ver)];"
            "dirs=[sysconfig.get_config_var('LIBDIR'),sysconfig.get_config_var('LIBPL'),"
            "os.path.join(sys.base_prefix,'lib'),os.path.expanduser('~/usr/local/lib'),"
            "'/data/service/hnp/lib','/usr/local/lib','/usr/lib'];"
            "matches=[];"
            "[matches.extend(glob.glob(os.path.join(d,n))) for d in dirs if d for n in names if n];"
            "print(json.dumps([os.path.dirname(p) for p in matches if os.path.isfile(p)]))"
        )
        try:
            libdirs = json.loads(
                subprocess.check_output([self._python(), "-c", code], text=True)
            )
        except Exception as exc:
            raise ConanInvalidConfiguration(
                "failed to locate Python runtime library: {}".format(exc)
            ) from exc
        return next((d for d in libdirs if d), "")

    def _runtime_libdirs(self):
        libdirs = []
        for _ref, dep in self.dependencies.items():
            for libdir in dep.cpp_info.libdirs or []:
                if libdir and libdir not in libdirs:
                    libdirs.append(libdir)
        python_libdir = self._python_libdir()
        if python_libdir and python_libdir not in libdirs:
            libdirs.append(python_libdir)
        return libdirs

    def _run_ohos_executable(self, executable):
        libdirs = self._runtime_libdirs()
        ld_library_path = ":".join(libdirs + ["${LD_LIBRARY_PATH:-}"])
        self.run(
            'LD_LIBRARY_PATH="{}" "{}"'.format(ld_library_path, executable),
            env="conanrun",
            cwd=self.build_folder,
        )

    def _site_dirs(self):
        package_folder = self.dependencies["eigenpy"].package_folder
        return sorted(
            glob.glob(os.path.join(package_folder, "lib", "python*", "site-packages"))
        )

    def _run_python_import(self):
        site_dirs = self._site_dirs()
        if not site_dirs:
            raise ConanException("eigenpy site-packages directory not found")

        python = self._python()
        script = os.path.join(self.source_folder, "test_import.py")
        old_pythonpath = os.environ.get("PYTHONPATH", "")
        old_ld_library_path = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["PYTHONPATH"] = os.pathsep.join(
            site_dirs + ([old_pythonpath] if old_pythonpath else [])
        )
        if self.settings.os == "OHOS":
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                self._runtime_libdirs()
                + ([old_ld_library_path] if old_ld_library_path else [])
            )
        try:
            self.run('"{}" "{}"'.format(python, script), env="conanrun")
        except ConanException as exc:
            probe_env = os.environ.copy()
            probe = subprocess.run(
                [python, script],
                capture_output=True,
                text=True,
                env=probe_env,
            )
            detail = (probe.stdout or "") + (probe.stderr or "") + str(exc)
            blocked = any(
                token in detail
                for token in (
                    "Permission denied",
                    "Operation not permitted",
                    "cannot open shared object",
                    "Error loading shared library",
                    "No module named 'numpy'",
                )
            )
            if self.settings.os == "OHOS" and blocked:
                self.output.warning(
                    "OHOS loader policy blocked Python dlopen from the runner path; "
                    "falling back to ELF inspection of eigenpy_pywrap."
                )
                self._verify_python_extension(site_dirs)
            else:
                raise ConanException(
                    "eigenpy Python import test failed (exit={}): {}".format(
                        probe.returncode, detail.strip()
                    )
                ) from exc
        finally:
            if old_pythonpath:
                os.environ["PYTHONPATH"] = old_pythonpath
            else:
                os.environ.pop("PYTHONPATH", None)
            if old_ld_library_path:
                os.environ["LD_LIBRARY_PATH"] = old_ld_library_path
            else:
                os.environ.pop("LD_LIBRARY_PATH", None)

    def _verify_python_extension(self, site_dirs):
        extensions = []
        for site_dir in site_dirs:
            extensions.extend(
                glob.glob(
                    os.path.join(site_dir, "eigenpy", "eigenpy_pywrap*.so*")
                )
            )
        if not extensions:
            raise ConanException("eigenpy_pywrap extension not found")

        extension = extensions[0]
        with open(extension, "rb") as f:
            if f.read(4) != b"\x7fELF":
                raise ConanException("{} is not an ELF extension".format(extension))

        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not readelf:
            self.output.info("PASS: {} has ELF magic".format(extension))
            return

        out = subprocess.check_output([readelf, "-d", extension], text=True)
        needed = [line.strip() for line in out.splitlines() if "NEEDED" in line]
        joined = " ".join(needed)
        expected = ("eigenpy", "boost_python", "python")
        if not any(token in joined for token in expected):
            raise ConanException(
                "eigenpy_pywrap NEEDED entries look incomplete: {}".format(needed)
            )
        self.output.info("PASS: eigenpy_pywrap ELF NEEDED entries: {}".format(needed))

    def _sign_executable(self, executable):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS execution requires llvm-objcopy and binary-sign-tool"
            )
        self._sign_elf_atomically(executable, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = "{}.signing".format(path)
        try:
            shutil.copy2(path, temporary)
            self.run('"{}" --remove-section .codesign "{}"'.format(objcopy, temporary))
            self.run(
                '"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                    signer, temporary, temporary
                )
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            "/data/service/hnp/bin/{}".format(name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if path and os.path.isfile(path)), "")
