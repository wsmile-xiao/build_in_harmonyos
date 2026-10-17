#!/usr/bin/env python3
"""Conan recipe for girara — user interface library for zathura."""

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class GiraraConan(ConanFile):
    name = "girara"
    version = "2026.07.07"
    package_type = "library"
    description = "User interface library for zathura (datastructures/utils/template)"
    license = "Zlib"
    homepage = "https://pwmt.org/projects/girara"
    url = "https://github.com/pwmt/girara"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("glib/2.84.0")

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # glib/gobject/gio all provided by system pkg-config; forbid meson wraps.
        tc.project_options["wrap_mode"] = "nodownload"
        # skip doxygen docs and unit tests in the package build
        tc.project_options["docs"] = "disabled"
        tc.project_options["tests"] = "false"
        # upstream default_options sets c_std=c23 (needs clang 16+); CI clang 15
        # only knows c2x (the C23 draft alias). Override to c2x so configure passes.
        tc.project_options["c_std"] = "c2x"
        tc.generate()
        # conan MesonToolchain 不把 ar/ranlib 写进 native file，meson 按裸名 llvm-ar
        # 探归档器，而 clang 工具链在 /data/service/hnp/bin，PATH 上无 llvm-ar 时
        # configure 报 "Unknown linker(s): [['llvm-ar']]"。从 c 编译器同目录推导
        # llvm-ar/llvm-ranlib 全路径，注入 conan_meson_native.ini 的 [binaries] 段。
        import os as _os
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        _cc = _ce.get("c") or ""
        _bindir = _os.path.dirname(_cc) if _os.path.sep in _cc else ""
        _ar = _rl = None
        if _bindir:
            _arc = _os.path.join(_bindir, "llvm-ar")
            if _os.path.isfile(_arc):
                _ar = _arc
                _rlc = _os.path.join(_bindir, "llvm-ranlib")
                if _os.path.isfile(_rlc):
                    _rl = _rlc
        _nf = _os.path.join(self.generators_folder, "conan_meson_native.ini")
        if _ar and _os.path.isfile(_nf):
            with open(_nf) as _f:
                _c = _f.read()
            if "\nar =" not in _c and "[binaries]" in _c:
                _ins = "[binaries]\nar = '%s'\n" % _ar
                if _rl:
                    _ins += "ranlib = '%s'\n" % _rl
                _c = _c.replace("[binaries]\n", _ins, 1)
                with open(_nf, "w") as _f:
                    _f.write(_c)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        if self.settings.os != "OHOS":
            return
        # meson install rewrites rpath after link, breaking the linker self-sign.
        # Strip old .codesign + binary-sign-tool -selfSign 1 re-sign so OHOS dlopen works.
        import glob, os
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        # 与 generate() 保持一致：从 C 编译器路径推导工具链目录，
        # 避免 CI 工具链路径变更后硬编码 /data/service/hnp/bin 失效。
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        _cc = _ce.get("c") or ""
        _bindir = os.path.dirname(_cc) if os.path.sep in _cc else ""
        if not _bindir:
            raise ConanException(
                "OHOS signing requires tools.build:compiler_executables to be set"
            )
        objcopy = os.path.join(_bindir, "llvm-objcopy")
        signer = os.path.join(_bindir, "binary-sign-tool")
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise ConanException(
                "OHOS shared library signing tools are unavailable at %s" % _bindir
            )
        for so in sos:
            # .codesign section may not exist on first build; only warn on failure
            ret = self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null'.format(oc=objcopy, f=so), ignore_errors=True)
            if ret != 0:
                self.output.warn("llvm-objcopy returned %d for %s (may be first build, no .codesign)" % (ret, so))
            ret = self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so), ignore_errors=True)
            if ret != 0:
                raise ConanException(
                    "binary-sign-tool failed with exit code %d for %s" % (ret, so)
                )

    def package_info(self):
        self.cpp_info.libs = ["girara"]
        # girara public headers install to include/girara/ (girara.h etc.)
        self.cpp_info.includedirs = ["include/girara", "include"]
        self.cpp_info.set_property("cmake_file_name", "girara")
        self.cpp_info.set_property("cmake_target_name", "girara::girara")
        self.cpp_info.set_property("pkg_config_name", "girara")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
