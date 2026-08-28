#!/usr/bin/env python3
"""Consumer test for Boost compiled components, including Boost.Python."""

import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class BoostMorpheusComponentsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()
        tc = CMakeToolchain(self)
        py = self._discover_python()
        tc.cache_variables["Python_EXECUTABLE"] = py["executable"]
        tc.cache_variables["Python_ROOT_DIR"] = py["prefix"]
        tc.cache_variables["Python_INCLUDE_DIR"] = py["include_dir"]
        tc.cache_variables["Python_LIBRARY"] = py["library"]
        tc.cache_variables["Python_FIND_STRATEGY"] = "LOCATION"
        if self.settings.os == "OHOS":
            gnu_ld_flag = "-fuse-ld=/data/service/hnp/bin/ld"
            for linker_flag in (
                "CMAKE_EXE_LINKER_FLAGS",
                "CMAKE_SHARED_LINKER_FLAGS",
                "CMAKE_MODULE_LINKER_FLAGS",
            ):
                tc.variables[linker_flag] = gnu_ld_flag
        self.output.info(
            "FindPython tips: exe={} include={} lib={} ver={}".format(
                py["executable"], py["include_dir"], py["library"], py["ver"]
            )
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built consumer cannot run on the build host.")
            return

        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(
            self.cpp.build.bindirs[0], "test_boost_morpheus_components" + suffix
        )
        if self.settings.os == "OHOS":
            self._sign_executable(executable)
            python_libdir = os.path.dirname(self._discover_python()["library"])
            command = 'LD_LIBRARY_PATH="{}:${{LD_LIBRARY_PATH:-}}" "{}"'.format(
                python_libdir, executable
            )
            self.run(command, env="conanrun", cwd=self.build_folder)
            return

        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)

    def _discover_python(self):
        candidates = [
            os.environ.get("BOOST_PYTHON"),
            os.environ.get("EIGENPY_PYTHON"),
            shutil.which("python3.12"),
            shutil.which("python3"),
            os.path.expanduser("~/usr/local/bin/python3"),
            "/data/service/hnp/bin/python3",
            "/data/app/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3",
        ]
        executable = next((c for c in candidates if c and os.path.isfile(c)), None)
        if not executable:
            raise ConanInvalidConfiguration(
                "python3 not found; Boost.Python test requires CPython 3.12"
            )

        code = (
            "import json,os,sys,sysconfig;"
            "inc=sysconfig.get_path('include');"
            "incpy=sysconfig.get_config_var('INCLUDEPY') or inc;"
            "d=dict(exe=sys.executable,inc=inc,incpy=incpy,"
            "prefix=sys.base_prefix,ver=sysconfig.get_python_version(),"
            "libdir=sysconfig.get_config_var('LIBDIR'),"
            "libpl=sysconfig.get_config_var('LIBPL'));"
            "m=[l.split()[-1] for l in open('/proc/self/maps') "
            "if 'libpython3.12.so' in l] if os.path.exists('/proc/self/maps') else [];"
            "d['libpython']=m[0] if m else '';"
            "print(json.dumps(d))"
        )
        try:
            info = json.loads(
                subprocess.check_output([executable, "-c", code], text=True)
            )
        except Exception as exc:
            raise ConanInvalidConfiguration(
                "failed to query Python sysconfig from {}: {}".format(
                    executable, exc
                )
            ) from exc

        if info["ver"] != "3.12":
            raise ConanInvalidConfiguration(
                "Boost.Python test is locked to Python 3.12; found {} at {}".format(
                    info["ver"], executable
                )
            )

        ver = info["ver"]
        root = os.path.dirname(os.path.dirname(os.path.realpath(executable)))
        include_candidates = [
            info.get("incpy"),
            info.get("inc"),
            os.path.join(info.get("prefix") or "", "include", "python{}".format(ver)),
            os.path.join(root, "include", "python{}".format(ver)),
            os.path.expanduser("~/usr/local/include/python{}".format(ver)),
            "/data/service/hnp/include/python{}".format(ver),
            "/usr/local/include/python{}".format(ver),
            "/usr/include/python{}".format(ver),
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
            raise ConanInvalidConfiguration(
                "Python.h not found for {}. Checked: {}".format(
                    executable, [d for d in include_candidates if d]
                )
            )

        library = self._libpython_file(executable, info)
        return {
            "executable": executable,
            "include_dir": include_dir,
            "library": library,
            "prefix": info.get("prefix") or root,
            "ver": ver,
        }

    def _libpython_file(self, executable, info):
        libpython = info.get("libpython") or ""
        if libpython and os.path.isfile(libpython):
            return libpython

        root = os.path.dirname(os.path.dirname(os.path.realpath(executable)))
        candidates = [
            info.get("libpl"),
            info.get("libdir"),
            os.path.join(info.get("prefix") or "", "lib"),
            os.path.join(root, "lib"),
            os.path.expanduser("~/usr/local/lib"),
            "/data/service/hnp/lib",
            "/usr/local/lib",
            "/usr/lib",
        ]
        for directory in candidates:
            if not directory:
                continue
            matches = glob.glob(os.path.join(directory, "libpython3.12.so"))
            matches.extend(glob.glob(os.path.join(directory, "libpython3.12.so.*")))
            matches = [m for m in matches if os.path.isfile(m)]
            if matches:
                return sorted(matches)[0]

        raise ConanInvalidConfiguration(
            "libpython3.12.so not found for {}. Checked: {}".format(
                executable, [d for d in candidates if d]
            )
        )

    def _sign_executable(self, executable):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy and binary-sign-tool"
            )
        self._sign_elf_atomically(executable, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1'
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
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")
