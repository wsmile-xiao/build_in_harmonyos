#!/usr/bin/env python3
"""Conan recipe for xine-lib 1.2.13 (libxine) — HarmonyOS PC adaptation.

xine-lib is the media library behind the xine video player. Upstream ships no
automated test suite (no `TESTS=`/`check_PROGRAMS`, `make check` is a no-op);
the real upstream test entry point is the `xmltest` noinst program in
src/xine-utils (built with -DXINE_XML_PARSER_TEST), which test_package/ runs
against real XML documents together with OHOS-specific checks.

Optional plugins (X11/OpenGL/ALSA/DirectFB/vdpau/...) are feature-gated by
configure and stay disabled on OHOS because their dependencies are absent;
the only mandatory third-party dependency is zlib.
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XinelibConan(ConanFile):
    name = "xine-lib"
    version = "1.2.13"
    description = "xine-lib (libxine) — free media player library"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/xine/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # libxine loads its plugins (xineplug_*.so) with dlopen(), so the core
        # library itself must be shared.
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        # Everything else (X11, OpenGL, ALSA, DirectFB, vdpau, ...) is feature
        # gated by configure and auto-disabled when the dependency is missing.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E490: keep the autotools helper scripts executable — some checkouts and
        # patch application can drop the mode bits, after which config.guess /
        # configure fail with "Permission denied" under the HMDFS mount.
        self.run('for f in configure config.guess config.sub install-sh missing '
                 'compile depcomp ar-lib; do if [ -f "$f" ]; then chmod +x "$f"; fi; done')
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream registers no TESTS=/check_PROGRAMS targets ("make check" is a
        # no-op everywhere). Its only real upstream test entry point is the
        # xmltest noinst program, built here from src/xine-utils with
        # -DXINE_XML_PARSER_TEST; run it against a generated XML document so
        # every build exercises the XML lexer/parser.
        sample = os.path.join(self.build_folder, "xmltest-sample.xml")
        save(self, sample,
             '<?xml version="1.0" encoding="UTF-8"?>\n'
             '<catalog>\n'
             '  <book id="1"><title>xine-lib</title><author>xine team</author></book>\n'
             '  <book id="2"><title>OHOS</title><author>OpenHarmony</author></book>\n'
             '</catalog>\n')
        self.run('./src/xine-utils/xmltest "%s" > xmltest.out 2>&1' % sample)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool *.la wrappers embed build-time paths.
        for la_file in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la_file)

    def package_info(self):
        self.cpp_info.libs = ["xine"]
        self.cpp_info.set_property("pkg_config_name", "libxine")
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # libxine resolves its plugins at runtime from $XINE_PLUGIN_PATH.
        plugins_root = os.path.join(self.package_folder, "lib", "xine", "plugins")
        if os.path.isdir(plugins_root):
            for entry in sorted(os.listdir(plugins_root)):
                sub = os.path.join(plugins_root, entry)
                if os.path.isdir(sub):
                    self.runenv_info.prepend_path("XINE_PLUGIN_PATH", sub)
