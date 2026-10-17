#!/usr/bin/env python3
"""Conan recipe for zathura-pdf-mupdf — PDF plugin for zathura using MuPDF.

The plugin is a runtime dlopen object: it exports the
``zathura_plugin_<API>_<ABI>`` definition struct and resolves zathura/girara
symbols from the host process at load time, so the build only needs the
zathura *plugin API headers* (vendored via patch, taken from zathura
2026.05.20) — no link-time zathura library exists yet as a conan package
(pending PR feat/zathura-2026.05.20).

MuPDF comes from the published ``mupdf-tools/1.27.2`` package which ships
``libmupdf.a`` + ``libmupdf-third.a`` (PIC) and the full ``mupdf/`` header
set; a hand-written ``mupdf.pc`` in generate() exposes it to meson's
``dependency('mupdf', version: '>=1.26')`` lookup (same layout Debian's
libmupdf-dev uses).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


def _ohos_linker_libxml2_workaround(conanfile):
    """Make the OHOS SDK linker loadable on CI workers.

    The OHOS SDK's lld depends on libxml2.so.16 which ships inside the SDK's
    own llvm/lib directory, outside the default loader path — every link then
    fails with "clang-15: error: unable to execute command". Prepend that lib
    dir to LD_LIBRARY_PATH when it provides libxml2.so.16 (no-op when the
    default linker already works).
    """
    ce = conanfile.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
    cc = ce.get("c") or ""
    if not cc:
        return
    cc_dir = os.path.dirname(os.path.realpath(cc))
    for cand in (os.path.join(cc_dir, "..", "lib"), os.path.join(cc_dir, "lib")):
        libdir = os.path.normpath(cand)
        if os.path.isfile(os.path.join(libdir, "libxml2.so.16")):
            old = os.environ.get("LD_LIBRARY_PATH", "")
            if libdir not in old.split(":"):
                os.environ["LD_LIBRARY_PATH"] = libdir + (":" + old if old else "")
            return


class ZathuraPdfMupdfConan(ConanFile):
    name = "zathura-pdf-mupdf"
    version = "2026.05.10"
    package_type = "library"
    description = "PDF plugin for zathura using MuPDF renderer"
    license = "MIT"
    homepage = "https://pwmt.org/projects/zathura-pdf-mupdf"
    url = "https://github.com/pwmt/zathura-pdf-mupdf"

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
        self.requires("girara/2026.07.07")
        self.requires("glib/2.84.0")
        self.requires("cairo/1.18.4")
        self.requires("mupdf-tools/1.27.2")

    def generate(self):
        PkgConfigDeps(self).generate()
        # meson.build looks up dependency('mupdf', version: '>=1.26'); the
        # mupdf-tools conan package ships the static libs + headers but no
        # pkg-config metadata, so provide a mupdf.pc pointing at its package
        # root (mirrors Debian's libmupdf-dev .pc, including -lmupdf-third).
        mupdf = self.dependencies["mupdf-tools"]
        libdir = mupdf.cpp_info.libdirs[0]
        includedir = mupdf.cpp_info.includedirs[0]
        with open(os.path.join(self.generators_folder, "mupdf.pc"), "w") as f:
            f.write(
                "Name: mupdf\n"
                "Description: MuPDF rendering library (from mupdf-tools conan package)\n"
                "Version: 1.27.2\n"
                "Libs: -L{s} -lmupdf -lmupdf-third -lm\n"
                "Cflags: -I{i}\n".format(s=libdir, i=includedir)
            )
        tc = MesonToolchain(self)
        # upstream default_options sets c_std=c23 (clang 16+); CI clang 15
        # only knows c2x (the C23 draft alias)
        tc.project_options["c_std"] = "c2x"
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["tests"] = "disabled"
        tc.project_options["pdf"] = "enabled"
        # install the plugin into <prefix>/lib/zathura (zathura's own
        # plugindir default; avoids the pkg-config zathura lookup)
        tc.project_options["plugindir"] = "lib/zathura"
        tc.generate()
        # conan MesonToolchain doesn't put ar/ranlib into the native file;
        # meson probes bare "llvm-ar" and configure fails when it is not on
        # PATH. Derive full paths next to the C compiler and inject them.
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = ce.get("c") or ""
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        ar = rl = None
        if bindir:
            arc = os.path.join(bindir, "llvm-ar")
            if os.path.isfile(arc):
                ar = arc
                rlc = os.path.join(bindir, "llvm-ranlib")
                if os.path.isfile(rlc):
                    rl = rlc
        nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if ar and os.path.isfile(nf):
            with open(nf) as f:
                content = f.read()
            if "\nar =" not in content and "[binaries]" in content:
                ins = "[binaries]\nar = '%s'\n" % ar
                if rl:
                    ins += "ranlib = '%s'\n" % rl
                content = content.replace("[binaries]\n", ins, 1)
                with open(nf, "w") as f:
                    f.write(content)

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os in ("Linux", "OHOS"):
            _ohos_linker_libxml2_workaround(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        if self.settings.os != "OHOS":
            return
        import glob
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = ce.get("c") or ""
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        if not bindir:
            raise ConanException("OHOS signing requires tools.build:compiler_executables to be set")
        objcopy = os.path.join(bindir, "llvm-objcopy")
        signer = os.path.join(bindir, "binary-sign-tool")
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise ConanException("OHOS signing tools are unavailable at %s" % bindir)
        for so in sos:
            # .codesign may not exist on first build; only warn on failure
            ret = self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null'.format(oc=objcopy, f=so),
                           ignore_errors=True)
            if ret != 0:
                self.output.warn("llvm-objcopy returned %d for %s (may be first build, no .codesign)" % (ret, so))
            # meson install rewrites rpath after link, breaking the linker
            # self-sign; strip + re-sign so OHOS dlopen works
            ret = self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so),
                           ignore_errors=True)
            if ret != 0:
                raise ConanException("binary-sign-tool failed with exit code %d for %s" % (ret, so))

    def package_info(self):
        # plugin module, installed to <prefix>/lib/zathura/pdf-mupdf.so
        self.cpp_info.libs = ["pdf-mupdf"]
        self.cpp_info.libdirs = ["lib/zathura"]
        self.cpp_info.set_property("cmake_file_name", "zathura-pdf-mupdf")
        self.cpp_info.set_property("cmake_target_name", "zathura-pdf-mupdf::pdf-mupdf")
        self.cpp_info.set_property("pkg_config_name", "zathura-pdf-mupdf")
