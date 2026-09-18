#!/usr/bin/env python3
"""Consumer test for libzimg 3.0.6 (autotools build).

Links against the packaged library via cpp_info (the same layout the
pkg-config file advertises) and runs a real zimg filter graph through the
public C API, plus the OHOS-specific NEON depth-path verification.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class LibzimgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = self._resolve_tool(compilers.get("cpp"), "clang++")
        dep = self.dependencies["libzimg"].cpp_info

        exe = os.path.join(self.build_folder, "test_libzimg")
        cmd = [
            *self._exec_tool(cxx),
            "-std=c++14",
            os.path.join(self.source_folder, "test.cpp"),
            "-o",
            exe,
        ]
        for include_dir in dep.includedirs:
            cmd.append("-I" + include_dir)
        for lib_dir in dep.libdirs:
            cmd.append("-L" + lib_dir)
        for lib in dep.libs:
            cmd.append("-l" + lib)
        for system_lib in dep.system_libs:
            cmd.append("-pthread" if system_lib == "pthread" else "-l" + system_lib)
        # the shared lib links libc++_shared.so (OHOS runtime)
        cmd.append("-lc++" if str(self.settings.os) == "OHOS" else "")

        self.run(" ".join(shlex.quote(part) for part in cmd if part))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            return
        exe = os.path.join(self.build_folder, "test_libzimg")
        # libzimg.so NEEDED libc++_shared.so from the OHOS SDK; the system
        # /system/lib64 only carries the __h-namespace libc++.so. Run with
        # an explicit env (subprocess; ConanFile.run's wrapper mangles the
        # inline prefix).
        import subprocess
        run_env = dict(os.environ)
        parts = [p for p in run_env.get("LD_LIBRARY_PATH", "").split(os.pathsep) if p]
        # the tested package's lib dir (so libzimg.so.2 resolves) and the
        # OHOS SDK libc++_shared.so dir
        lib_dirs = getattr(self.dependencies["libzimg"].cpp_info, "libdirs", [])
        for libdir in lib_dirs:
            if libdir not in parts:
                parts.insert(0, libdir)
        if str(self.settings.os) == "OHOS":
            sdk = ("/data/service/hnp/ohos-sdk.org/"
                   "ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos")
            if sdk not in parts:
                parts.insert(0, sdk)
        run_env["LD_LIBRARY_PATH"] = os.pathsep.join(parts)
        proc = subprocess.run([exe], env=run_env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.output.info(proc.stdout.decode(errors="replace"))
        if proc.returncode != 0:
            raise Exception(f"test_libzimg failed with rc={proc.returncode}")

    def _resolve_tool(self, configured, fallback):
        if configured and os.path.exists(configured):
            return configured
        found = shutil.which(fallback)
        if found:
            return found
        if configured:
            bindir = os.path.dirname(configured) if os.path.isabs(configured) else ""
            candidate = os.path.join(bindir, fallback) if bindir else ""
            if candidate and os.path.exists(candidate):
                return candidate
        home_candidate = os.path.join(os.path.expanduser("~"), "usr", "local", "bin", fallback)
        if os.path.exists(home_candidate):
            return home_candidate
        return fallback

    def _exec_tool(self, tool):
        if self._is_script(tool):
            return ["sh", tool]
        return [tool]

    @staticmethod
    def _is_script(path):
        if not path or not os.path.isfile(path):
            return False
        try:
            with open(path, "rb") as handle:
                return handle.read(2) == b"#!"
        except OSError:
            return False
