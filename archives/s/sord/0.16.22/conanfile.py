import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                                get)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps


class SordConan(ConanFile):
    name = "sord"
    version = "0.16.22"
    description = "C library for storing and querying RDF data"
    license = "ISC"
    homepage = "https://drobilla.net/software/sord"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
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

    def requirements(self):
        self.requires("serd/0.32.9")
        self.requires("zix/0.8.1-git.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["docs"] = "disabled"
        tc.project_options["lint"] = "false"
        tc.project_options["man"] = "disabled"
        tc.project_options["tests"] = "enabled"
        tc.project_options["tools"] = "enabled"
        PkgConfigDeps(self).generate()
        tc.generate()
        self._inject_meson_archiver()
        self._inject_host_lib_path()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if not cross_building(self):
            meson.test()

    def package(self):
        Meson(self).install()
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_sordi()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "*", src=os.path.join(self.source_folder, "LICENSES"),
             dst=os.path.join(self.package_folder, "licenses", "LICENSES"), keep_path=True)

    def package_info(self):
        self.cpp_info.libs = ["sord-0"]
        self.cpp_info.includedirs = ["include/sord-0"]
        self.cpp_info.set_property("cmake_file_name", "sord")
        self.cpp_info.set_property("cmake_target_name", "sord::sord")
        self.cpp_info.set_property("pkg_config_name", "sord-0")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    def _inject_host_lib_path(self):
        """Ensure the OHOS SDK's bundled libxml2 resolves before linker lld runs.

        CI's build host has a foreign libxml2.so.16 (missing symbols such as
        xmlFreeDoc) shadowing the SDK's own copy via LD_LIBRARY_PATH / default
        search paths. The SDK's linker lld loads libxml2 on its own RPATH and
        fails with "Error loading shared library libxml2.so.16 ... xmlFreeDoc:
        symbol not found". Writing LD_LIBRARY_PATH into a `conanbuild_*` script
        (auto-sourced by the aggregated conanbuild.sh) reliably exports it to
        every child process including ninja→clang→lld (matches aaphoto recipe).
        """
        compiler_exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compiler_exes.get("c") or "/data/service/hnp/bin/clang"
        cc_real = os.path.realpath(cc)
        bindir = os.path.dirname(cc_real) if os.path.sep in cc_real else ""
        llvm_lib = os.path.normpath(os.path.join(bindir, "..", "lib")) if bindir else ""
        if not llvm_lib or not os.path.isdir(llvm_lib):
            llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if not os.path.isdir(llvm_lib):
            return
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", llvm_lib.replace("\\", "/"))
        env.vars(self, scope="build").save_script("conanbuild_libpath")

    def _inject_meson_archiver(self):
        compiler_exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = compiler_exes.get("ar")
        ranlib = compiler_exes.get("ranlib")
        if not ar:
            cc = compiler_exes.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(ranlib_candidate):
                        ranlib = ranlib_candidate

        pkg_config = self.conf.get("tools.gnu:pkg_config", default="", check_type=str) or ""
        if not pkg_config or not os.path.isfile(pkg_config):
            pkg_config = "/data/service/hnp/bin/pkg-config"

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue

            insertion = "[binaries]\n"
            if ar:
                insertion += "ar = '{0}'\n".format(ar.replace("\\", "/"))
                if ranlib:
                    insertion += "ranlib = '{0}'\n".format(ranlib.replace("\\", "/"))
            if pkg_config and os.path.isfile(pkg_config) and "\npkg-config =" not in content:
                insertion += "pkg-config = '{0}'\n".format(pkg_config.replace("\\", "/"))

            if insertion.strip() == "[binaries]":
                continue

            content = content.replace("[binaries]\n", insertion, 1)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _sign_ohos_sordi(self):
        sordi = os.path.join(self.package_folder, "bin", "sordi")
        if not os.path.isfile(sordi):
            return

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warning("OHOS signing tools not found; skip sordi signing")
            return

        signed = sordi + ".signed"
        self.run(f'"{objcopy}" --remove-section .codesign "{sordi}" 2>/dev/null || true')
        self.run(f'"{signer}" sign -inFile "{sordi}" -outFile "{signed}" -selfSign 1')
        os.replace(signed, sordi)
        os.chmod(sordi, 0o755)
