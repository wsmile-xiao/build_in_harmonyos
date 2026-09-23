#!/usr/bin/env python3
"""Conan recipe — pakchois 0.4 (autotools / libtool)

pakchois (Joe Orton) is a thin PKCS#11 wrapper library: it loads PKCS#11
provider modules (DSOs) and forwards an object-oriented C API, without
depending on any particular crypto toolkit. This recipe adapts the 2008
autoconf 2.61 / libtool release to OpenHarmonyOS (aarch64).
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PakchoisConan(ConanFile):
    name = "pakchois"
    version = "0.4"
    description = "Thin PKCS#11 wrapper library (DSO loading + object-oriented C interface)"
    license = "LGPL-2.0-or-later"
    homepage = "http://www.manyfish.co.uk/pakchois/"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.guess (2006) cannot guess the OHOS build machine (uname -s=HarmonyOS),
        # so pin the triplet explicitly. config.sub (2006-09-20) does not know aarch64 —
        # patched in build() below to accept it; -linux-gnu is already supported.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        # po/ gettext tree is only needed for NLS; --disable-nls makes po/Makefile
        # hit its empty `all-no:` target, so no gettext tooling is required.
        tc.configure_args.append("--disable-nls")
        # configure.ac hard-checks -lpthread/-ldl (AC_CHECK_LIB(...,[AC_MSG_ERROR])).
        # On OHOS musl both are folded into libc. Seeding the autoconf cache variables
        # skips the probe (autoconf treats `VAR=value` arguments as cache/env presets),
        # and libtool links the shared lib without --no-undefined so the symbols resolve
        # from libc at runtime.
        tc.configure_args.append("ac_cv_lib_pthread_pthread_mutex_lock=yes")
        tc.configure_args.append("ac_cv_lib_dl_dlopen=yes")
        tc.generate()

    def _patch_config_sub(self):
        """Teach the 2006-09-20 config.sub the aarch64 CPU family.

        It has no aarch64 at all; add it exactly where arm/arm-* already live so
        `aarch64-unknown-linux-gnu` canonicalizes like the 32-bit ARM triples.
        """
        _sub = os.path.join(self.source_folder, "config.sub")
        if not os.path.isfile(_sub):
            self.output.warning("config.sub not found, aarch64 patch skipped")
            return
        replace_in_file(self, _sub,
                        "| arc | arm | arm[bl]e | arme[lb] | armv[2345] | armv[345][lb] | avr | avr32 \\",
                        "| aarch64 | aarch64_be | arc | arm | arm[bl]e | arme[lb] | armv[2345] | armv[345][lb] | avr | avr32 \\")
        replace_in_file(self, _sub,
                        "| alphapca5[67]-* | alpha64pca5[67]-* | arc-* \\",
                        "| alphapca5[67]-* | alpha64pca5[67]-* | arc-* \\\n\t| aarch64-* | aarch64_be-* \\")

    def build(self):
        apply_conandata_patches(self)
        # HMDFS: temp dirs that config.status creates with umask 077 end up without
        # group-write permission, so conftest writes fail. Relax to 022 (same fix as
        # the enscript/p11-kit recipes).
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True) + \
                    glob.glob(os.path.join(self.source_folder, "**", "config.guess"), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as _f:
                    _text = _f.read()
            except OSError:
                continue
            if "umask 077" in _text:
                with open(_cfg, "w", encoding="utf-8") as _f:
                    _f.write(_text.replace("umask 077", "umask 022"))
        self._patch_config_sub()
        # Device default TMPDIR lives on HMDFS; point autotools conftest temp files at a
        # writable dir inside the conan build folder.
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["pakchois"]
        self.cpp_info.set_property("pkg_config_name", "pakchois")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
