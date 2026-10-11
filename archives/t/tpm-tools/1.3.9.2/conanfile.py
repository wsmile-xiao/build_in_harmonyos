#!/usr/bin/env python3
"""Conan recipe for tpm-tools 1.3.9.2 — TSS 1.2 command line tools.

tpm-tools is the user/admin front end of the TCG Software Stack: the
``tpm_*`` command line programs plus the ``libtpm_unseal`` library.  It ships
an autotools project without a generated ``configure``, links against
``libtspi`` (trousers) and needs libcrypto for the PKCS#12 handling.
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TpmToolsConan(ConanFile):
    name = "tpm-tools"
    version = "1.3.9.2"
    description = "TSS 1.2 command line tools (tpm_*) and the libtpm_unseal library"
    license = "CPL-1.0"
    homepage = "https://trousers.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # Ships libtpm_unseal (library + headers) next to the tpm_* command line
    # tools: "application" would hide the include/library dirs from consumers.
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("tpm-tools is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # libtspi (Tspi_Context_Create …) plus libcrypto (PEM_read_X509)
        self.requires("trousers/0.3.15")
        self.requires("openssl/3.5.6.1")
        # AM_GNU_GETTEXT([external]) links against libintl; musl/HarmonyOS has
        # no libintl of its own.
        self.requires("gettext/0.22.5")

    def build_requirements(self):
        # The release tarball has no generated configure; the worker ships a
        # working autoconf 2.72 but no automake/libtool/libm4 tooling, and
        # AM_GNU_GETTEXT needs autopoint (gettext).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("pkg-config/0.29.2")

    def layout(self):
        basic_layout(self)
        # In-source build: config.h and the generated Makefiles live next to
        # the sources and the SUBDIRS makefiles extend CPPFLAGS in place.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # PKCS#11 support needs opencryptoki, which is not published; upstream
        # auto-disables it when the header is missing, be explicit about it.
        tc.configure_args.append("--disable-pkcs11-support")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()

    def _autopoint(self):
        found = shutil.which("autopoint")
        if found:
            return found
        for candidate in sorted(glob.glob("/data/service/hnp/gettext.org/*/bin/autopoint")):
            if os.path.exists(candidate):
                return candidate
        return ""

    def build(self):
        apply_conandata_patches(self)
        os.environ["PWD"] = self.build_folder
        # Upstream's bootstrap.sh prepares the gettext layout itself
        # (po_/ -> po/, plus an empty m4/Makefile.am) before running autoreconf;
        # autopoint then installs the real gettext infrastructure on top.
        self.run("mkdir -p po m4 && cp -R po_/* po/ && touch m4/Makefile.am",
                 env="conanbuild")
        # Everything runs under the worker's system perl: PERL5LIB is narrowed
        # to automake's module directory so the registry perl package's XS
        # modules are never loaded (they fail to relocate on this platform).
        # AM_GNU_GETTEXT_VERSION makes autoreconf run autopoint, which lives in
        # the worker's gettext HNP prefix (not on PATH), so it is passed
        # explicitly together with its own directory.
        autopoint = self._autopoint()
        prefix = extra = ""
        if autopoint:
            prefix = 'PATH="%s:$PATH"' % os.path.dirname(autopoint)
            # autopoint has the build machine's install prefix baked in, so its
            # data directory (archive.dir.tar.xz holds the per-version gettext
            # infrastructure) has to be pointed at explicitly.
            datadir = os.path.join(os.path.dirname(os.path.dirname(autopoint)),
                                   "share", "gettext")
            extra = 'AUTOPOINT="%s" gettext_datadir="%s"' % (autopoint, datadir)
        self.run('%s %s PERL5LIB="%s" autoreconf -fi'
                 % (prefix, extra, self._automake_share()), env="conanbuild")
        self._patch_generated_configure()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        self._audit_upstream_tests()

    def _automake_share(self):
        for dep in self.dependencies.build.values():
            share = os.path.join(dep.package_folder, "share")
            if not os.path.isdir(share):
                continue
            for name in sorted(os.listdir(share)):
                if name.startswith("automake-"):
                    return os.path.join(share, name)
        return ""

    def _patch_generated_configure(self):
        """HMDFS fixes for the freshly generated configure script."""
        path = os.path.join(self.build_folder, "configure")
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        original = text
        text = text.replace(
            'ac_pwd=`pwd` && test -n "$ac_pwd" &&',
            'ac_pwd=`pwd` 2>/dev/null || ac_pwd=$PWD\ntest -n "$ac_pwd" &&')
        text = text.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`(umask 022 && mktemp -d "./confXXXXXX") 2>/dev/null`')
        text = text.replace(
            'tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
            'tmp=./conf$$-$RANDOM\n  (umask 022 && mkdir "$tmp")')
        if text != original:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)

    def _audit_upstream_tests(self):
        # The release only carries one unregistered shell script
        # (test/tpm_changeownerauth01.sh, listed in EXTRA_DIST and driving a
        # real TPM); no Makefile.am registers a check target.
        self.run("grep -nE 'check_PROGRAMS|^TESTS|check-local|^check:' Makefile.am "
                 "src/*/Makefile.am lib/Makefile.am || true")
        self.run("ls -la test 2>/dev/null || true")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                if name.endswith(".la"):
                    os.remove(os.path.join(libdir, name))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["tpm_unseal"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin", "sbin"]
