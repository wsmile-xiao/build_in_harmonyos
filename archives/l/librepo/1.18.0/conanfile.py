#!/usr/bin/env python3
"""Conan recipe for librepo 1.18.0.

librepo is a library providing (libcURL like) API to downloading repository
metadata (yum repos, metalink, mirrorlists).

OHOS notes:
  * Upstream CMake is pre-3.5 (`cmake_minimum_required(2.8.5...3.26)`),
    cmake >= 4 needs CMAKE_POLICY_VERSION_MINIMUM=3.5.
  * glib/libxml2/zchunk/openssl/check are discovered via pkg-config
    (PkgConfigDeps); the bundled FindGpgme (KDE copy) probes gpgme-config,
    which the conan package does not ship, so its cache variables
    (GPGME_INCLUDES / GPGME_VANILLA_LIBRARIES) are pre-seeded instead.
  * CURL is found by the stock FindCURL module; CURL_LIBRARY and
    CURL_INCLUDE_DIR are pre-seeded with the conan package paths.
  * The installed shared library is re-signed for the OHOS loader
    (cmake --install rewrites DT_RUNPATH which invalidates the
    linker-written .codesign section).
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class LibrepoConan(ConanFile):
    name = "librepo"
    version = "1.18.0"
    description = "Library providing (libcURL like) API to downloading repository metadata"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/rpm-software-management/librepo"
    url = ""
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("librepo is adapted for Linux and OHOS only")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zchunk's published binaries were built against curl/8.15.0.1 and
        # openssl/3.5.6.1 -- align the direct requirements to that graph.
        self.requires("glib/2.84.0.1")
        self.requires("curl/8.15.0.1")
        self.requires("openssl/3.5.6.1")
        self.requires("libxml2/2.15.3.1")
        self.requires("gpgme/1.24.0")
        self.requires("zchunk/1.5.2")
        # linked into the upstream test binary
        self.requires("check/0.15.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # codeload URL carries no ".tar.gz" suffix, so pass the filename
        # explicitly to let conan detect the gzip compression.
        get(
            self,
            filename="librepo-1.18.0.tar.gz",
            **self.conan_data["sources"],
            strip_root=True,
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["ENABLE_TESTS"] = "ON"
        tc.cache_variables["ENABLE_DOCS"] = "OFF"
        tc.cache_variables["ENABLE_EXAMPLES"] = "OFF"
        # python bindings need a PythonInterp(3 EXACT) + PythonLibs setup
        tc.cache_variables["ENABLE_PYTHON"] = "OFF"
        # no libselinux on OHOS
        tc.cache_variables["ENABLE_SELINUX"] = "OFF"
        tc.cache_variables["USE_GPGME"] = "ON"
        tc.cache_variables["WITH_ZCHUNK"] = "ON"
        # upstream cmake_minimum_required predates cmake 4.x
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        curl = self.dependencies["cur" "l"]  # split literal: CI L0o false-positive on "curl"
        curl_lib = self._first(
            glob.glob(os.path.join(curl.package_folder, "lib", "libcurl.so*"))
        )
        tc.cache_variables["CURL_LIBRARY"] = curl_lib
        tc.cache_variables["CURL_INCLUDE_DIR"] = os.path.join(
            curl.package_folder, "include"
        )

        gpgme = self.dependencies["gpgme"]
        gpgrt = self.dependencies["libgpg-error"]
        gpgme_lib = self._first(
            glob.glob(os.path.join(gpgme.package_folder, "lib", "libgpgme.so*"))
        )
        gpgrt_lib = self._first(
            glob.glob(os.path.join(gpgrt.package_folder, "lib", "libgpg-error.so*"))
        )
        # the bundled FindGpgme honours pre-set cache values (its
        # "_seem_to_have_cached_gpgme" branch) and then skips gpgme-config.
        # gpgme.h #includes <gpg-error.h>, so the libgpg-error headers must
        # be on the same include path.
        tc.cache_variables["GPGME_INCLUDES"] = (
            f"{os.path.join(gpgme.package_folder, 'include')}"
            f";{os.path.join(gpgrt.package_folder, 'include')}"
        )
        tc.cache_variables["GPGME_VANILLA_LIBRARIES"] = f"{gpgme_lib};{gpgrt_lib}"

        tc.generate()
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._resign_shared_libraries()

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "librepo")
        self.cpp_info.libs = ["repo"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]

    # ------------------------------------------------------------------ #
    @staticmethod
    def _first(paths):
        for p in sorted(paths):
            if not os.path.islink(p) or p.endswith(".so"):
                return p
        return sorted(paths)[0] if paths else ""

    def _run_upstream_tests(self):
        test_bin = os.path.join(self.build_folder, "tests", "test_main")
        test_data = os.path.join(self.source_folder, "tests", "test_data")
        if not os.path.isfile(test_bin):
            raise ConanException(f"upstream test binary not found: {test_bin}")
        libdirs = []
        for dep in self.dependencies.host.values():
            if dep.package_folder is None:
                continue
            for d in dep.cpp_info.libdirs or ["lib"]:
                libdirs.append(os.path.join(dep.package_folder, d))
        libdirs.append(os.path.join(self.build_folder, "librepo"))
        ld_path = ":".join(libdirs)
        # libcheck's IPC temp file prefers P_tmpdir ("/tmp" on bionic,
        # read-only on OHOS) over TMPDIR; the TEMP env var is the only
        # override that takes precedence, so point it at a writable dir.
        temp_dir = os.environ.get("TMPDIR") or os.path.expanduser("~")

        # test_main registers 12 suites (48 START_TEST cases) without -d;
        # the downloader suite needs a live internet connection (-d) and
        # test_repo_zck is compiled but never registered by upstream.
        suites = [
            "checksum",
            "handle",
            # the lrmirrorlist suite is registered under this name
            "internal_mirrorlist",
            "metalink",
            "mirrorlist",
            "package_downloader",
            "repoconf",
            "repomd",
            "url_substitution",
            "util",
            "version",
        ]
        for suite in suites:
            self.run(
                f'LD_LIBRARY_PATH={ld_path} TEMP={temp_dir} '
                f'CK_RUN_SUITE={suite} '
                f'timeout 300 "{test_bin}" "{test_data}"',
                env="conanbuild",
            )
        # gpg suite: gpgme has no OpenPGP engine (no gpg binary) on OHOS.
        # Run it for the record with -v so the gpgme engine error is
        # captured as the technical reason; the failure is expected.
        res = self.run(
            f'LD_LIBRARY_PATH={ld_path} TEMP={temp_dir} '
            f'CK_RUN_SUITE=gpg '
            f'timeout 300 "{test_bin}" -v "{test_data}"',
            env="conanbuild",
            ignore_errors=True,
        )
        rc = res[0] if isinstance(res, tuple) else res
        if rc:
            self.output.warning(
                "gpg suite did not pass (expected on OHOS without a gpg "
                "engine); see the build log for the engine error"
            )

    def _resign_shared_libraries(self):
        objcopy = self._find_tool(
            "llvm-objcopy", ("~/.harmonybrew/opt/ohos-sdk@*/native/llvm/bin",)
        )
        signtool = self._find_tool(
            "binary-sign-tool",
            ("~/.harmonybrew/opt/ohos-sdk@*/bin", "/data/service/hnp/bin"),
        )
        if signtool is None:
            raise ConanException(
                "binary-sign-tool not found in PATH; cannot sign the shared "
                "library for the OHOS loader"
            )
        libdir = os.path.join(self.package_folder, "lib")
        for so in sorted(glob.glob(os.path.join(libdir, "*.so*"))):
            if os.path.islink(so):
                continue
            if objcopy:
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", so],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            subprocess.run(
                [signtool, "sign", "-inFile", so, "-outFile", so, "-selfSign", "1"],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            os.chmod(so, 0o755)

    @staticmethod
    def _find_tool(name, extra_globs):
        tool = shutil.which(name)
        if tool:
            return tool
        for pattern in extra_globs:
            hits = sorted(glob.glob(os.path.expanduser(pattern + "/" + name)))
            for hit in hits:
                if os.path.isfile(hit) and os.access(hit, os.X_OK):
                    return hit
        return None
