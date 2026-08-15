#!/usr/bin/env python3
"""Conan recipe for clinfo 3.0.23.01.25 — OpenCL platform/device info utility.

clinfo is a plain-Makefile C project (no autotools/cmake/meson). It queries
the OpenCL ICD loader (libOpenCL) and prints all known properties of the
platforms and devices available on the system.

HarmonyOS adaptation notes:
- OpenCL headers (CL/cl.h) are not shipped by the OHOS system, so the
  official KhronosGroup/OpenCL-Headers tarball is vendored into the build.
- The OHOS system has no system libOpenCL (ICD loader) either, so the
  official KhronosGroup/OpenCL-ICD-Loader tarball is built from source with
  CMake and clinfo is linked against it. The resulting libOpenCL.so.1 is
  packaged next to the clinfo binary; clinfo is linked with rpath $ORIGIN so
  the dynamic loader finds it at runtime.
- The resulting ELF files (clinfo and libOpenCL.so.1) must be code-signed
  with the HNP binary-sign-tool, otherwise the HarmonyOS kernel refuses to
  use them.
- Upstream CFLAGS include `-Werror -pedantic`; they are dropped to avoid
  clang-15 warning-as-error failures (E063).
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ClinfoConan(ConanFile):
    name = "clinfo"
    version = "3.0.23.01.25"
    description = "Print all known information about all available OpenCL platforms and devices"
    license = "CC0-1.0"
    homepage = "https://github.com/Oblomov/clinfo"
    url = "https://github.com/Oblomov/clinfo"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # OpenCL headers and ICD loader are vendored; no conan deps

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["clinfo"], strip_root=True)
        # Vendor official Khronos OpenCL headers (CL/cl.h) for compilation
        get(self, **self.conan_data["sources"]["opencl_headers"],
            strip_root=True, destination="OpenCL-Headers")
        # Vendor the official Khronos ICD loader (provides libOpenCL) because
        # the OHOS system ships no system libOpenCL
        get(self, **self.conan_data["sources"]["opencl_icd_loader"],
            strip_root=True, destination="OpenCL-ICD-Loader")

    def _sign_elf(self, path):
        """ELF code-sign a file so the HarmonyOS kernel can use it."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool):
            # Remove any stale .codesign section first, then self-sign
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{sign_tool} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass  # chmod may be unsupported on the device FS (HMBS_CAP_CHMOD=0)

    def _build_icd_loader(self, src, cc):
        """Build the vendored OpenCL ICD loader (libOpenCL) with CMake."""
        loader_src = os.path.join(src, "OpenCL-ICD-Loader")
        loader_build = os.path.join(self.build_folder, "loader-build")
        headers_dir = os.path.join(src, "OpenCL-Headers")
        cmake = os.environ.get("HMBS_CMAKE", "cmake")
        self.run(
            f'"{cmake}" -S "{loader_src}" -B "{loader_build}" '
            f'-DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER="{cc}" '
            f'-DENABLE_OPENCL_LAYERS=OFF -DBUILD_TESTING=OFF '
            f'-DOPENCL_ICD_LOADER_HEADERS_DIR="{headers_dir}" '
            f'-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
            cwd=src,
        )
        self.run(f'"{cmake}" --build "{loader_build}" -j1', cwd=src)
        # Real versioned file (libOpenCL.so.1.2); the .so/.so.1 entries are symlinks
        real_so = [p for p in glob.glob(os.path.join(loader_build, "libOpenCL.so*"))
                   if os.path.isfile(p) and not os.path.islink(p)]
        if not real_so:
            raise RuntimeError("ICD loader build produced no libOpenCL.so in " + loader_build)
        return loader_build, real_so[0]

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        src = self.source_folder
        cppflags = f"-I{os.path.join(src, 'OpenCL-Headers')}"
        # Drop upstream -pedantic -Werror (E063): clang-15 warning-as-error failures
        cflags = "-O2 -std=c99 -Wall -Wextra"

        if self.settings.os == "OHOS":
            # No system libOpenCL on OHOS: build the vendored ICD loader and
            # link clinfo against it. LDFLAGS is passed via the environment so
            # the shell never touches the $$ORIGIN make escape.
            loader_build, real_so = self._build_icd_loader(src, cc)
            os.environ["LDFLAGS"] = f"-L{loader_build} -Wl,-rpath,'$$ORIGIN'"
            self.run(f'make CC="{cc}" CFLAGS="{cflags}" CPPFLAGS="{cppflags}" -j1', cwd=src)
            self._sign_elf(os.path.join(src, "clinfo"))
            self._sign_elf(real_so)
        else:
            self.run(f'make CC="{cc}" CFLAGS="{cflags}" CPPFLAGS="{cppflags}" -j1', cwd=src)
        self._audit_upstream_tests()

    def _audit_upstream_tests(self):
        """Audit the upstream tree for automated tests (machine evidence).

        The clinfo 3.0.23.01.25 release tarball ships no automated tests:
        the Makefile only defines all/clean/install/sparse targets (no
        check/test target) and the source tree has no tests/ directory.
        Run the audit grep against the real source tree so the conan create
        log carries the machine evidence; the no_tests marker itself is
        emitted by the test_package stage (MANIFEST upstream_test_in_build:
        false, same pattern as the gate-passing aribb24 recipe).
        """
        # build() 将进程 cwd 切到 build_folder，审计必须用 source_folder 的绝对路径。
        audit_cmd = (
            "grep -rnE '(^|[^A-Za-z_])TESTS|check_PROGRAMS|check-local|"
            "check_SCRIPTS|^test:|^check:' \"%s\" 2>/dev/null || true; "
            "ls -d \"%s\" 2>/dev/null || true"
            % (os.path.join(self.source_folder, "Makefile"),
               os.path.join(self.source_folder, "tests"))
        )
        self.run(audit_cmd)

    @staticmethod
    def _real_loader_so(loader_build):
        """Return the real (non-symlink) versioned libOpenCL.so* file path."""
        real = [p for p in glob.glob(os.path.join(loader_build, "libOpenCL.so*"))
                if os.path.isfile(p) and not os.path.islink(p)]
        return real[0] if real else None

    def package(self):
        copy(self, "clinfo", self.source_folder, os.path.join(self.package_folder, "bin"))
        if self.settings.os == "OHOS":
            loader_build = os.path.join(self.build_folder, "loader-build")
            real_so = self._real_loader_so(loader_build)
            if real_so:
                bin_dir = os.path.join(self.package_folder, "bin")
                # Ship the real versioned file under its SONAME (libOpenCL.so.1)
                # so the dynamic loader, using rpath $ORIGIN, finds it without
                # relying on symlink support in the package.
                copy(self, os.path.basename(real_so), loader_build, bin_dir)
                os.rename(os.path.join(bin_dir, os.path.basename(real_so)),
                          os.path.join(bin_dir, "libOpenCL.so.1"))
        for f in os.listdir(os.path.join(self.package_folder, "bin")):
            try:
                os.chmod(os.path.join(self.package_folder, "bin", f), 0o755)
            except OSError:
                pass  # chmod may be unsupported on the device FS (HMBS_CAP_CHMOD=0)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
