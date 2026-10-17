#!/usr/bin/env python3
"""Conan recipe for libnfs 5.0.3 (CMake).

libnfs is a client library for accessing NFS shares over a network.  The
upstream project also ships four command line utilities (nfs-ls, nfs-cat,
nfs-cp and nfs-stat); they are built with ENABLE_UTILS=ON and declared in the
software-level commands.json (R38).

HarmonyOS PC / aarch64 build notes
----------------------------------
* CMake reports "System is unknown to cmake: Platform/HarmonyOS" and therefore
  does not inject -Wl,-soname on this platform.  A shared libnfs.so ends up
  without a SONAME, so the utilities record a relative build-tree path
  ("../lib/libnfs.so") in DT_NEEDED and fail to start after installation.
  Following the repository convention for non-system libraries we build a
  static archive (shared=False by default); this also makes the CLI tools
  self-contained (only libc.so in DT_NEEDED — verified with readelf).
* Upstream installs the CLI with install(FILES ...), which loses the
  executable bit and does not fix up RPATH.  Patch 0003 replaces it with
  install(TARGETS ... RUNTIME DESTINATION ...).
* Patches 0001/0002 add the <sys/uio.h> probe that the autotools build has
  (AC_CHECK_HEADERS([sys/uio.h])) but the CMake build was missing, which
  previously caused an implicit declaration of writev() (an int/ssize_t
  truncation hazard on aarch64).

The upstream test suite (tests/*.sh, 50 CTest cases) requires `sudo exportfs`
to start a kernel NFS export; HarmonyOS PC has no exportfs / /proc/fs/nfsd so
those tests cannot run here (see notes.md and test_package/MANIFEST.yml).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibnfsConan(ConanFile):
    name = "libnfs"
    version = "5.0.3"
    description = "Client library for accessing NFS shares over a network"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/sahlberg/libnfs"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libnfs depends only on libc / pthread; the talloc+tevent and fuse
        # integrations detected by CMake are optional and left disabled.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: everything is passed through the Conan CMake toolchain, never via
        # shell environment variables.
        tc = CMakeToolchain(self)
        # Build a static archive by default: the HarmonyOS CMake platform is
        # unknown, so shared libraries are produced without a SONAME.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # R38: build the bundled CLI tools (nfs-ls/nfs-cat/nfs-cp/nfs-stat);
        # they are declared in archives/l/libnfs/commands.json.
        tc.variables["ENABLE_UTILS"] = "ON"
        # The upstream test suite needs an NFS server and is not shipped.
        tc.variables["ENABLE_TESTS"] = "OFF"
        tc.variables["ENABLE_EXAMPLES"] = "OFF"
        # CMake >= 4 dropped compatibility with cmake_minimum_required(<3.5);
        # upstream declares 3.2.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The CMake target is "nfs" (libnfs.a / -lnfs); headers live in nfsc/.
        self.cpp_info.libs = ["nfs"]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):  # R32
            self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.set_property("cmake_file_name", "libnfs")
        self.cpp_info.set_property("cmake_target_name", "libnfs::nfs")
        self.cpp_info.set_property("pkg_config_name", "libnfs")
