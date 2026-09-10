#!/usr/bin/env python3
"""Conan recipe for libfyaml 0.9.6 (Autotools, OHOS-adapted).

- No mandatory external dependency: libyaml (yaml-0.1) is an OPTIONAL
  compatibility layer; configure falls back to HAVE_LIBYAML=0 when it is
  absent, which is the configuration validated on OHOS (aarch64-linux-ohos).
- The official tag tarball does NOT ship a generated `configure`; the recipe
  runs bootstrap.sh first. m4/pkg.m4 must be present before autoreconf so
  PKG_CHECK_MODULES expands (system pkg-config aclocal dir is injected via
  export of m4-pkg.m4). config.guess/config.sub carry HarmonyOS
  (linux-ohos) detection patches applied AFTER bootstrap (autoreconf --install
  would overwrite them), see patches/.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibfyamlConan(ConanFile):
    name = "libfyaml"
    version = "0.9.6"
    description = "Fast YAML parser and emitter library"
    license = "MIT"
    homepage = "https://github.com/pantoniou/libfyaml"
    url = "https://github.com/pantoniou/libfyaml"
    topics = ("yaml", "parser", "emitter")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)
        # pkg-config aclocal macro (pkg.m4) needed by configure.ac PKG_CHECK_MODULES
        copy(self, "m4-pkg.m4", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        # libyaml (yaml-0.1) is optional upstream (compatibility layer);
        # validated build uses HAVE_LIBYAML=0 and needs no external requires.
        pass

    def build_requirements(self):
        # The official tag tarball ships no generated `configure`: build()
        # runs bootstrap.sh (autoreconf), which needs aclocal (automake) and
        # libtoolize (libtool). The remote CI sandbox has the autoconf suite
        # on PATH but no aclocal/automake (Can't exec "aclocal": No such file
        # or directory). Pull in exactly automake + libtool as tool_requires
        # (resolved with the *build* profile, published at ohpcd) - the same
        # minimal, CI-proven set used by abiword-plugin-* / argp-standalone.
        # autoconf, m4 and pkg-config are already provided by the build host
        # (autoreconf runs from /data/service/hnp/bin), and pkg.m4 for
        # PKG_CHECK_MODULES is supplied via m4-pkg.m4 export (ACLOCAL_PATH).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()
        # m4 macros dir of this recipe (export_sources): expose to aclocal
        # through ACLOCAL_PATH (pkg.m4 for PKG_CHECK_MODULES expansion).
        self.buildenv_info.append_path("ACLOCAL_PATH", self.export_sources_folder)

    def build(self):
        # 1) m4/pkg.m4 must be in place BEFORE autoreconf/bootstrapping
        import shutil
        shutil.copy(os.path.join(self.export_sources_folder, "m4-pkg.m4"),
                    os.path.join(self.source_folder, "m4", "pkg.m4"))
        # 2) generate configure (official tag has no generated configure);
        #    env=conanbuild makes the tool_requires (automake/aclocal, autoconf,
        #    libtool, m4, pkgconf) available on PATH inside bootstrap.sh.
        self.run("sh bootstrap.sh", cwd=self.source_folder, env="conanbuild")
        # 3) config.guess/config.sub OHOS patches AFTER bootstrap
        #    (autoreconf --install overwrites them otherwise)
        apply_conandata_patches(self)
        # 4) HMDFS temp-dir workaround (E136): config.status creates ./confXXXXXX
        #    with umask 077 -> drwx--S--- unwritable by the current user;
        #    patch the freshly generated configure (which embeds config.status).
        cfg = os.path.join(self.source_folder, "configure")
        with open(cfg, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        content = content.replace("umask 077", "umask 002")
        with open(cfg, "w", encoding="utf-8") as f:
            f.write(content)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["fyaml"]
        self.cpp_info.set_property("cmake_file_name", "libfyaml")
        self.cpp_info.set_property("cmake_target_name", "libfyaml::libfyaml")
        self.cpp_info.set_property("pkg_config_name", "libfyaml")