"""Conan recipe — cairomm 1.14.5.1 (Meson build).

cairomm is a C++ wrapper for the cairo graphics library, providing
the cairomm-1.0 ABI used by gtkmm-3.0.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class CairommConan(ConanFile):
    name = "cairomm"
    version = "1.14.5.1"
    description = "C++ wrapper for the cairo graphics library (cairomm-1.0 ABI, for gtkmm-3.0)"
    license = "LGPL-2.0-or-later"
    homepage = "https://www.cairographics.org/cairomm/"
    url = "https://www.cairographics.org/"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        self.requires("cairo/1.18.4", transitive_headers=True, transitive_libs=True)
        self.requires("libsigc/2.12.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Remove meson subproject wraps so meson falls back to pkg-config
        # for sigc++-2.0 and cairo (provided by Conan dependencies).
        rm(self, "*.wrap", os.path.join(self.source_folder, "subprojects"))

    def generate(self):
        # PkgConfigDeps generates .pc files for ALL dependencies (direct +
        # transitive) into the generators folder, which MesonToolchain adds
        # to pkg_config_path.  This makes meson find cairo, sigc++-2.0,
        # zlib, fontconfig, freetype, pixman, libpng, etc.
        PkgConfigDeps(self).generate()
        toolchain = MesonToolchain(self)
        toolchain.project_options["maintainer-mode"] = "false"
        toolchain.project_options["default_library"] = "shared" if self.options.shared else "static"
        toolchain.project_options["build-documentation"] = "false"
        toolchain.project_options["build-examples"] = "false"
        toolchain.project_options["build-tests"] = "false"
        # Force clang++ to use ld.lld (Unix frontend) instead of the `lld`
        # generic driver.  In CI sandboxes `lld` depends on libxml2.so.16
        # which is not on the dynamic linker search path, while `ld.lld`
        # is self-contained.  meson's linker detection honours -fuse-ld.
        ld_lld = "/data/service/hnp/bin/ld.lld"
        toolchain.c_link_args.append(f"-fuse-ld={ld_lld}")
        toolchain.cpp_link_args.append(f"-fuse-ld={ld_lld}")
        toolchain.generate()
        self._inject_meson_tools()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # 原生 OHOS worker：meson install 改写了 rpath，.so 需要重新 codesign
        # 才能 dlopen/执行（E135，与 glibmm/pangomm 配方一致）。
        # 缺此步骤时 OHOS dlopen 对签名无效的 .so 报 Permission denied（实测）。
        # 交叉 Docker SDK 无 binary-sign-tool → 跳过。
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        candidates_objcopy = [
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "",
        ]
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            candidates_objcopy.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates_objcopy if p and os.path.isfile(p)), None)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign (cross/SDK env)")
            return
        for so in sos:
            if objcopy:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.libs = ["cairomm-1.0"]
        self.cpp_info.includedirs = ["include/cairomm-1.0", "lib/cairomm-1.0/include"]
        self.cpp_info.set_property("cmake_file_name", "cairomm-1.0")
        self.cpp_info.set_property("cmake_target_name", "cairomm-1.0::cairomm")
        self.cpp_info.set_property("pkg_config_name", "cairomm-1.0")
        self.cpp_info.requires = ["cairo::cairo", "libsigc::libsigc"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

    def _inject_meson_tools(self):
        """Inject ar/ranlib/pkg-config/ld into Meson machine files (OHOS).

        On HarmonyOS the LLVM bin dir is not on PATH by default, so Meson
        cannot locate ``llvm-ar`` / ``llvm-ranlib``.  We also force the
        linker to ``ld.lld`` (the Unix frontend) instead of the ``lld``
        generic driver — ``lld`` depends on ``libxml2.so.16`` which is not
        guaranteed to be on the dynamic linker search path in CI sandboxes,
        while ``ld.lld`` is self-contained.
        """
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            ar = None
            ranlib = None
            ld = None
            for directory in (bindir, "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin"):
                if not ar:
                    candidate = os.path.join(directory, "llvm-ar")
                    if os.path.isfile(candidate):
                        ar = candidate
                if not ranlib:
                    candidate = os.path.join(directory, "llvm-ranlib")
                    if os.path.isfile(candidate):
                        ranlib = candidate
                if not ld:
                    candidate = os.path.join(directory, "ld.lld")
                    if os.path.isfile(candidate):
                        ld = candidate
            pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
            if not pkg_config or not os.path.isfile(str(pkg_config)):
                pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insert = []
            if ar and "\nar =" not in content:
                insert.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                insert.append(f"ranlib = '{ranlib}'")
            if ld and "\nld =" not in content:
                insert.append(f"ld = '{ld}'")
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                insert.append(f"pkg-config = '{pkg_config}'")
            if insert:
                content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1)
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)
