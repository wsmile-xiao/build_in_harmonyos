#!/usr/bin/env python3
"""Conan test_package for openmama 6.3.2.

Builds and runs two real consumers of the package:

  test_openmama_c    exercises the MAMA C API: version, open/close lifecycle,
                     loading of the stub middleware bridge that ships with the
                     package and of the qpid (AMQP) middleware bridge that links
                     the qpid-proton package
  test_openmama_cpp  the same lifecycle through the C++ bindings, which also
                     proves libmamacpp is linkable and usable

Both binaries assert internally and return the number of failed checks, so a
plain run is the assertion (R34: they call into the package's API instead of
printing a banner).
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, cmake_layout


class OpenMamaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The resource pool API this test exercises is built on APR pools
        # (mama/resourcepool.h includes <apr_pools.h>), so the consumer needs
        # the apr package to create the pool it passes in.
        self.requires("apr/1.7.6.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _find_ohos_tool(self, name):
        """Locate one of the OHOS SDK/device tools next to the compiler."""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        compiler = compilers.get("c", "") or compilers.get("cpp", "")
        candidates = (
            os.path.join(os.path.dirname(compiler), name) if compiler else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        )
        return next((path for path in candidates if path and os.path.isfile(path)), "")

    def _sign_executable(self, path):
        """OHOS refuses to exec an unsigned binary, and a signature is a
        content hash, so the freshly linked consumer has to be signed before
        it can be run."""
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "running the OHOS consumers requires llvm-objcopy and binary-sign-tool")
        unsigned = path + ".unsigned"
        try:
            shutil.copy2(path, unsigned)
            self.run('env -u LD_LIBRARY_PATH %s --remove-section .codesign "%s" '
                     '2>/dev/null || true' % (objcopy, unsigned))
            self.run('env -u LD_LIBRARY_PATH %s sign -inFile "%s" -outFile "%s" '
                     '-selfSign 1' % (signer, unsigned, path))
        finally:
            if os.path.exists(unsigned):
                os.remove(unsigned)

    def _libcxx_shared_dir(self):
        """Directory holding the SDK's libc++_shared.so.

        The consumers link libc++ dynamically and that shared library is not in
        the default search path on OHOS, so its directory is located through
        the compiler instead of hardcoding an SDK version path.
        """
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "") or "clang++"
        try:
            probe = subprocess.run([cxx, "-print-file-name=libc++_shared.so"],
                                   capture_output=True, text=True, timeout=60)
        except Exception as exc:  # pragma: no cover - environment dependent
            self.output.warning("libc++_shared.so introspection failed: %s" % exc)
            return None
        path = probe.stdout.strip()
        # clang echoes the name back when it cannot resolve it
        if path.startswith("/") and os.path.isfile(path):
            return os.path.dirname(path)
        self.output.warning("could not locate libc++_shared.so")
        return None

    def _extend_library_search_path(self):
        """Add the directories the consumers need at run time.

        conanrun (VirtualRunEnv) prepends the lib directory of every package
        dependency to the ambient LD_LIBRARY_PATH, so only the SDK libc++ has
        to be contributed here for the binaries to load.
        """
        lib_dirs = []
        libcxx_dir = self._libcxx_shared_dir()
        if libcxx_dir:
            lib_dirs.append(libcxx_dir)
        current = os.environ.get("LD_LIBRARY_PATH", "")
        if current:
            lib_dirs.append(current)
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(lib_dirs)

    def test(self):
        self._extend_library_search_path()
        for binary in glob.glob(os.path.join(self.build_folder, "test_openmama_*")):
            if self.settings.os == "OHOS":
                self._sign_executable(binary)
            self.run(binary, env="conanrun")
