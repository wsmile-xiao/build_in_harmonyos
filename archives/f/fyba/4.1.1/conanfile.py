#!/usr/bin/env python3
"""Conan recipe for fyba 4.1.1 — OpenFYBA, SOSI geodata format library.

OpenFYBA is the source-code release of the FYBA library, distributed by the
Norwegian Mapping Authority (Kartverket / Statens kartverk), to read and
write files in the national geodata standard format SOSI.

Build notes (OHOS/HarmonyOS PC):
- The shipped `configure` (2014 vintage) cannot bootstrap on OHOS: it fails
  with "cannot find install-sh" (aux files absent) and "cannot guess build
  type" (uname -s = "HarmonyOS").  We therefore regenerate it with
  `autoreconf -fi` in build(); the regenerated config.sub understands the
  *-linux-ohos triplet (verified), so the OHOS triplet is passed explicitly
  and configure never runs the config.guess probe (same approach as
  argp-standalone / abiword-plugin-*).
- Tool requires automake + libtool for the autoreconf bootstrap (autoconf is
  pulled in by the automake dependency chain); the build host lacks system
  automake/aclocal/libtoolize.
- Upstream ships no unit tests in the 4.1.1 tag (README mentions a tests
  folder that is absent from the release tarball; verified via full tag
  listing).  The consumer test in test_package/ exercises the public
  HO_New / LC_* APIs and verifies the produced SOSI artifact instead.
- Produces three static/shared libraries: libfyba (SOSI), libfygm (GM
  geometry), libfyut (UT utilities).  Headers install to include/fyba/.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FybaConan(ConanFile):
    name = "fyba"
    version = "4.1.1"
    description = "OpenFYBA — SOSI geodata format reader/writer library (Kartverket)"
    license = "MIT"
    homepage = "https://github.com/kartverket/fyba"
    url = "https://github.com/kartverket/fyba"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # autoreconf bootstrap; autoconf comes via the automake dep chain
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("fyba is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        # 2014-era source uses the `register` keyword (UT1.cpp/UT2.cpp),
        # removed in strict ISO C++17; keep it as an accepted extension.
        tc.extra_cxxflags.append("-Wno-register")
        # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS");
        # pass the triplet explicitly (config.sub supports *-linux-ohos).
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # The shipped configure is 2014-vintage and cannot run on OHOS
        # (missing install-sh / cannot guess build type): regenerate it.
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114/E175: config.status creates its temp dir via
        # `(umask 077 && mktemp -d ./confXXXXXX)`; on the CI AppSpawn sandbox /
        # HMDFS-style storage the umask-077 dir is not writable, so
        # `cat >"$ac_tmp/defines.awk"` fails with "Permission denied" and
        # configure dies with "could not setup config headers machinery".
        # Relaxing to umask 022 keeps temp-dir semantics (scratch dir only,
        # removed after run) while letting the write succeed; identical
        # configure output. Same fix as argp-standalone / abiword-plugin-*.
        for _cfg in glob.glob(os.path.join(self.source_folder, "configure")):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    _text = f.read()
            except OSError:
                continue
            if "umask 077" in _text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(_text.replace("umask 077", "umask 022"))
                self.output.info("configure: umask 077 -> 022 (config.status temp dir writable)")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Remove libtool *.la wrappers
        import glob as _glob
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["fyba", "fygm", "fyut"]
        self.cpp_info.system_libs = ["m"]
        # fyba.h internally includes <fygm.h>/<fyut.h> with angle brackets,
        # and all three headers are installed under include/fyba/ — consumers
        # need both include/ (for <fyba/fyba.h>) and include/fyba/.
        self.cpp_info.includedirs = ["include", "include/fyba"]
        # fyut.h defines UT_INT64 only under `#ifdef LINUX` (and the library
        # itself is built with -DUNIX -DLINUX from the upstream Makefile.am);
        # public headers require these macros, so export them to consumers.
        self.cpp_info.defines = ["UNIX", "LINUX"]
        self.cpp_info.set_property("pkg_config_name", "fyba")
