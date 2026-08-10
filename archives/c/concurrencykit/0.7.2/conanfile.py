import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ConcurrencyKitConan(ConanFile):
    name = "concurrencykit"
    version = "0.7.2"
    description = "Concurrent data structures and synchronization primitives"
    license = "BSD-2-Clause"
    homepage = "https://github.com/concurrencykit/ck"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("concurrencykit supports Linux and OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("concurrencykit supports only OHOS armv8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cc = os.environ.get("CC", "clang")
        self.run(f'./configure CC="{cc}" --prefix=/usr', cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def test(self):
        self.run("test -f lib/libck.a", cwd=self.source_folder)

    def package(self):
        # The upstream Makefile's install-headers target hard-codes
        # mkdir -p //usr/include (prefix is honored for libs but not the
        # include dir), so `make install prefix=...` tries to write into
        # the read-only /usr/include and aborts. Bypass make install and
        # copy the built artifacts + headers into the package folder by hand.
        src = self.source_folder
        copy(self, "libck.a", src=os.path.join(src, "src"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "libck.so", src=os.path.join(src, "src"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        # The upstream Makefile links libck.so with SONAME 'libck.so.0', so
        # the dynamic loader looks up libck.so.0 by that SONAME at runtime.
        # Ship a sibling symlink libck.so.0 -> libck.so so the lookup resolves
        # in the package's lib/ (CMakeDeps already adds -Wl,-rpath to that dir).
        lib_dir = os.path.join(self.package_folder, "lib")
        os.symlink("libck.so", os.path.join(lib_dir, "libck.so.0"))
        # Copy the include/ tree PRESERVING the gcc/<arch>/ subdirs. ck_pr.h
        # is a dispatcher that #includes "gcc/aarch64/ck_pr.h" (arm inline asm)
        # when __aarch64__ is set; a flat *.h copy would land the gcc/x86_64/
        # ck_pr.h (x86 '+q'/'+a' asm constraints) on top of the dispatcher and
        # test_package compilation would pick the x86 version and abort.
        copy(self, "*.h", src=os.path.join(src, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)

    def package_info(self):
        self.cpp_info.libs = ["ck"]
        # Explicitly declare the libdirs so CMakeDeps generates an IMPORTED
        # target with IMPORTED_LOCATION pointing at libck.so, which lets the
        # linker embed an RPATH/runpath to the package's lib/ — without this,
        # the test_package binary has no RPATH and the dynamic loader cannot
        # find libck.so.0 (SONAME) at ctest runtime.
        self.cpp_info.libdirs = ["lib"]
