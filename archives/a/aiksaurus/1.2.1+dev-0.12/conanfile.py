#!/usr/bin/env python3
"""Conan recipe — aiksaurus 1.2.1+dev-0.12 (Autotools: configure + make).

English-language thesaurus library (Aiksaurus), used by AbiWord.
Produces libAiksaurus.so + two CLI tools (aiksaurus / caiksaurus)
+ thesaurus data files (words.dat / meanings.dat).

HarmonyOS adaptations (via patches declared in conandata.yml):
  0001-config.guess.patch - Upgrade to official GNU config.guess 2023-08-22
                            (adds HarmonyOS / aarch64-unknown-linux-ohos, E007)
  0002-config.sub.patch   - Upgrade to official GNU config.sub 2023-08-22
                            (adds linux-ohos triple, E007)
  0003-configure.patch    - Remove `umask 077` from temp-dir creation
                            (HMDFS permission fix, see abook E007 pattern)

Notes:
  - configure.ac uses AC_DISABLE_STATIC, so the library is shared-only.
    aiksaurus is NOT a system same-name library, so R26 (force-static) does
    not apply here.
  - GTK+ front-end is explicitly disabled (--with-gtk=no): no gtk2 dep.
  - Thesaurus data lives under share/aiksaurus/ (cpp_info.resdirs).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AiksaurusConan(ConanFile):
    name = "aiksaurus"
    version = "1.2.1+dev-0.12"
    description = "Aiksaurus — English-language thesaurus library (used by AbiWord)"
    license = "GPL-2.0-or-later"
    homepage = "http://aiksaurus.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies (autotools, std C++ only)
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS"), not == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "aiksaurus is only supported on Linux/OHOS, not "
                + str(self.settings.os)
            )
        # configure.ac uses AC_DISABLE_STATIC — shared-only library.
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "aiksaurus only supports shared=True (AC_DISABLE_STATIC)"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # R3: all source modifications via patches declared in conandata.yml
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # No GTK+ front-end (gtk+-2.0 is not available in OHOS PC env)
        tc.configure_args.append("--with-gtk=no")
        # configure.ac has AC_DISABLE_STATIC -> shared-only library.
        # aiksaurus is not a system same-name lib, so dynamic linking is fine.
        tc.configure_args.append("--enable-shared")
        # 2003-era code uses dynamic exception specs `throw(...)` and the
        # `register` storage specifier, both invalid in C++17 (profile sets
        # compiler.cppstd=17). Downgrade both diagnostics to warnings so the
        # old code still compiles (R33: flags come from Conan toolchain).
        tc.extra_cxxflags.append("-Wno-error=dynamic-exception-spec")
        tc.extra_cxxflags.append("-Wno-error=register")
        # Upstream configure.ac does AC_CHECK_FUNC(getenv) WITHOUT AC_DEFINE,
        # so config.h lacks HAVE_GETENV and the AIK_DATA_DIR env var override
        # for the thesaurus data path never takes effect. Define it here so
        # consumers can point AIK_DATA_DIR at the installed share/aiksaurus/.
        tc.extra_cflags.append("-DHAVE_GETENV=1")
        tc.extra_cxxflags.append("-DHAVE_GETENV=1")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Library: libAiksaurus.so (SONAME libAiksaurus-1.2.so.0)
        self.cpp_info.libs = ["Aiksaurus"]
        # Headers installed to <prefix>/include/Aiksaurus/{Aiksaurus.h,AiksaurusC.h}
        self.cpp_info.includedirs = ["include/Aiksaurus"]
        # Thesaurus data (words.dat / meanings.dat) under share/aiksaurus/
        self.cpp_info.resdirs = ["share/aiksaurus"]
        # CLI tools in bin/
        self.cpp_info.bindirs = ["bin"]
        # For pkg-config consumers
        self.cpp_info.set_property("pkg_config_name", "aiksaurus-1.0")
        # PATH for CLI tools in VirtualRunEnv
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
