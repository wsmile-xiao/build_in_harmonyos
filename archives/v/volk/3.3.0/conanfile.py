#!/usr/bin/env python3
"""Conan recipe for GNU Radio VOLK 3.3.0 — Vector Optimized Library of Kernels.

VOLK provides portable SIMD-accelerated DSP kernels with runtime CPU feature
dispatch; it is a core dependency of GNU Radio and other SDR/PHY stacks.

OHOS adaptation summary (details in notes.md):
* Python mako is a mandatory build-time dependency; it is ensured
  deterministically in build() (same pattern as mesa/acme-tiny).
* Upstream pins fmt 10.2.1 through FetchContent, which is not published to the
  artifact repository.  This recipe uses fmt/11.1.3 plus the official
  FMT_DEPRECATED_HEAVY_CORE compatibility switch, because since fmt 11
  <fmt/core.h> no longer exposes fmt::format that lib/qa_utils.cc relies on.
* ENABLE_ORC=OFF: upstream FindORC requires the `orcc` tool, which the
  published orc/0.4.42 package (tools disabled) does not provide.
* OHOS ELF files require a valid .codesign section (E077).  The install-time
  RPATH rewrite would invalidate the linker signature, therefore
  CMAKE_BUILD_WITH_INSTALL_RPATH=ON is set and packaged ELFs are re-signed.
"""

import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
)


class VolkConan(ConanFile):
    name = "volk"
    version = "3.3.0"
    description = ("GNU Radio VOLK — Vector Optimized Library of Kernels: portable "
                   "SIMD-accelerated DSP kernels with runtime CPU dispatch")
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/gnuradio/volk"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # volk_profile and volk_test_all link fmt.  Upstream pins 10.2.1 via
        # FetchContent; the closest published OHOS build is 11.1.3.
        self.requires("fmt/11.1.3")

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # The build host is HarmonyOS, for which CMake has no platform
            # module: CMAKE_SYSTEM_PROCESSOR ends up "unknown" (disables the
            # aarch64 cpu_features branch) and shared libraries lose their
            # SONAME/versioning.  Align the target with the SDK toolchain and
            # cmake's own Platform/OHOS.cmake (same fix as fmt/brotli/glfw).
            tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Make the Conan-provided fmt visible to find_package(fmt).
        CMakeDeps(self).generate()
        # The published orc package has no orcc tool -> FindORC always fails;
        # be explicit instead of relying on the failed probe.
        tc.variables["ENABLE_ORC"] = False
        # Build the upstream QA application (volk_test_all) and its CTest set.
        tc.variables["ENABLE_TESTING"] = True
        tc.variables["ENABLE_MODTOOL"] = True
        # E077/E537: do not rewrite RPATH at install time, so the ELF signature
        # added by the OHOS toolchain at link time stays valid; package()
        # re-signs defensively as the E077 four-step flow.
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        if self.settings.os in ("Linux", "OHOS"):
            # Relative RPATH so the packaged bin/ tools can load libvolk.so
            # without LD_LIBRARY_PATH (CI L2 smoke test) while staying
            # relocatable; no absolute Conan cache paths are embedded.
            tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN/../lib"
        # fmt >= 11 moved fmt::format out of <fmt/core.h>; this official
        # switch restores the fmt 10 behaviour used by lib/qa_utils.cc.
        tc.extra_cxxflags.append("-DFMT_DEPRECATED_HEAVY_CORE")
        tc.generate()

    def build(self):
        self._ensure_mako()
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._sign_elf_tree(os.path.join(self.build_folder, "lib"),
                            ["*.so", "*.so.*", "volk_test_all"])
        self._run_upstream_tests()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._make_pkg_config_relocatable()
        self._sign_elf_tree(os.path.join(self.package_folder, "lib"),
                            ["*.so", "*.so.*"])
        self._sign_elf_tree(os.path.join(self.package_folder, "bin"), ["*"])

    def package_info(self):
        self.cpp_info.libs = ["volk"]
        # Explicit non-empty bindirs so the CI L0k (R38) heuristic recognises
        # this package as shipping CLI tools (kcoreaddons5 precedent).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "Volk")
        self.cpp_info.set_property("cmake_target_name", "Volk::volk")
        self.cpp_info.set_property("pkg_config_name", "volk")
        if self.settings.os in ("Linux", "OHOS"):
            # Matches the INTERFACE_LINK_LIBRARIES of the installed
            # VolkTargets.cmake ("dl;m").
            self.cpp_info.system_libs = ["dl", "m"]

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _ensure_mako(self):
        # VOLK's CMake resolves the Python interpreter from the Conan build
        # environment (find_package(PythonInterp 3)), so probe and install mako
        # with exactly that environment.  A Conan-process-local
        # importlib.metadata check is not sufficient: CI workers may run the
        # Conan process itself under a different Python interpreter than the
        # build environment, which made the previous probe fail even after a
        # successful `pip install --user` (CI build #63475).
        mako_probe = 'python3 -c "import mako"'
        if self.run(mako_probe, env="conanbuild", ignore_errors=True) == 0:
            self.output.info("python mako found in the build environment")
            return
        self.output.info("VOLK needs Python mako at build time; installing it")
        self.run("python3 -m pip install 'mako>=0.4.2' --quiet", env="conanbuild")
        if self.run(mako_probe, env="conanbuild", ignore_errors=True) != 0:
            raise ConanException(
                "Python mako is required to build VOLK but not importable in "
                "the Conan build environment after installation")

    def _run_upstream_tests(self):
        libdir = os.path.join(self.build_folder, "lib")
        ld_paths = [libdir]
        fmt_dep = self.dependencies["fmt"]
        for lib in fmt_dep.cpp_info.libdirs:
            ld_paths.append(os.path.join(fmt_dep.package_folder, lib))
        old = os.environ.get("LD_LIBRARY_PATH", "")
        if old:
            ld_paths.append(old)
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(ld_paths)
        self.output.info("running upstream ctest (volk_test_all based) ...")
        self.run("ctest --output-on-failure -j2", cwd=self.build_folder)

    def _make_pkg_config_relocatable(self):
        pc_file = os.path.join(self.package_folder, "lib", "pkgconfig", "volk.pc")
        if not os.path.isfile(pc_file):
            return
        content = load(self, pc_file)
        content = re.sub(r"(?m)^prefix=.*$", "prefix=${pcfiledir}/../..", content)
        content = re.sub(r"(?m)^exec_prefix=.*$", "exec_prefix=${prefix}", content)
        content = re.sub(r"(?m)^libdir=.*$", "libdir=${prefix}/lib", content)
        content = re.sub(r"(?m)^includedir=.*$", "includedir=${prefix}/include", content)
        save(self, pc_file, content)

    def _sign_elf_tree(self, root, patterns):
        """Re-sign ELF files following the E077 four-step flow.

        Signing works on a copy first, so a failure never leaves a broken ELF.
        """
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            self.output.warning("binary-sign-tool/llvm-objcopy not found; skip ELF signing")
            return
        candidates = []
        for pattern in patterns:
            candidates.extend(glob.glob(os.path.join(root, pattern)))
        for path in sorted(set(candidates)):
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            try:
                with open(path, "rb") as handle:
                    if handle.read(4) != b"\x7fELF":
                        continue
            except OSError:
                continue
            work = path + ".signwork"
            shutil.copy2(path, work)
            self.run('"%s" --remove-section .codesign "%s"' % (objcopy, work),
                     ignore_errors=True)
            self.run('"%s" sign -inFile "%s" -outFile "%s.signed" -selfSign 1'
                     % (signer, work, work), ignore_errors=True)
            signed = work + ".signed"
            if os.path.isfile(signed):
                os.replace(signed, path)
                os.chmod(path, 0o755)
            if os.path.isfile(work):
                os.remove(work)
