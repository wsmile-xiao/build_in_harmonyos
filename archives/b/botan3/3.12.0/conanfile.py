import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class Botan3Conan(ConanFile):
    name = "botan3"
    version = "3.12.0"
    package_type = "library"
    description = "Botan 3 C++ cryptography library (C++20)"
    license = "BSD-2-Clause"
    homepage = "https://botan.randombit.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("cryptography", "security", "tls", "hash")

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/*"

    # Modules disabled for the OHOS clang-15 toolchain, see notes.md:
    # StrongSpan-dependent Kyber/Dilithium (and the ML-KEM/ML-DSA modules
    # layered on the same *_common code) fail to compile there, matching
    # the botan 3.6.1 adaptation record.
    _disabled_modules = (
        "kyber,kyber_90s,kyber_common,kyber_round3,ml_kem,"
        "dilithium,dilithium_aes,dilithium_common,dilithium_round3,ml_dsa"
    )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"botan3 is adapted for Linux/OHOS, got {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"botan3/3.12.0 is validated for OHOS armv8, got {self.settings.arch}"
            )
        if self.options.shared:
            raise ConanInvalidConfiguration("botan3/3.12.0 is packaged as a static library")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return executables.get("cpp", "c++")

    def build(self):
        apply_conandata_patches(self)
        # -march=... is required: Botan 3.12 tags AES/SHA/SM4 kernels with
        # function-level target("+crypto+aes") attributes, but OHOS clang-15's
        # arm_neon.h gates the intrinsics behind __ARM_FEATURE_* macros, which
        # the attribute does not define (verified on device). A global
        # -march armv8.2-a+crypto+sha3+sm4 makes all needed intrinsics
        # visible; runtime cpuid gating still selects the kernels.
        configure = (
            f'"{sys.executable}" "{os.path.join(self.source_folder, "configure.py")}" '
            f"--cc=clang --cc-bin=\"{self._compiler()}\" --os=linux --cpu=arm64 "
            f"--prefix=\"{self.package_folder}\" --build-targets=static,tests "
            f"--without-os-features=explicit_bzero --without-documentation "
            f"--cc-abi-flags=-march=armv8.2-a+crypto+sha3+sm4 "
            f"--disable-modules={self._disabled_modules} --link-method=copy"
        )
        self.run(configure, cwd=self.build_folder)
        self.run("make -j1", cwd=self.build_folder)
        # Botan's Makefile invokes 'ar crs libbotan-3.a <all .o>' as a single
        # very long command line. OHOS toybox shell silently truncates it, so
        # the archive is never produced. Recreate it with a glob (short command).
        if not os.path.isfile(os.path.join(self.build_folder, "libbotan-3.a")):
            self.run("rm -f libbotan-3.a && ar crs libbotan-3.a build/obj/lib/*.o",
                     cwd=self.build_folder)
        # Upstream test suite: make check runs ./botan-test with the absolute
        # --data-dir recorded in build_config.json. TMPDIR is consumed by the
        # 0005 patch (mkstemp redirection away from the read-only /tmp) and is
        # passed as a command prefix because ConanFile.run()'s env= argument
        # only accepts profile environment names, not dicts (CI #45083).
        self.run(f'TMPDIR="{self.build_folder}" make -j1 check', cwd=self.build_folder)

    def package(self):
        # configure.py / make run with cwd=self.build_folder, so the static
        # archive lands in build_folder root (not build_folder/lib).
        copy(self, "libbotan-3*.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        # Botan 3.12's configure stages public headers under
        # build/include/public/botan (partly via symlinks). Package them in
        # upstream's installed layout include/botan-3/botan and dereference
        # the symlinks (conan's copy() preserves them, which break once src/
        # is absent from the package).
        import shutil
        shutil.copytree(
            os.path.join(self.build_folder, "build", "include", "public"),
            os.path.join(self.package_folder, "include", "botan-3"),
            symlinks=False,
            dirs_exist_ok=True,
        )
        copy(self, "license.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = ["include/botan-3"]
        self.cpp_info.libs = ["botan-3"]
        self.cpp_info.set_property("cmake_file_name", "botan3")
        self.cpp_info.set_property("cmake_target_name", "botan3::botan3")
        self.cpp_info.set_property("pkg_config_name", "botan-3")
