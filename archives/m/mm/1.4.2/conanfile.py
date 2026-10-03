#!/usr/bin/env python3
"""Conan recipe for the OSSP mm shared-memory allocation library (libmm)."""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _drop_umask_077(conanfile):
    """E114: HMDFS forces the setgid bit onto directories, which turns the
    `(umask 077 && mktemp -d ./confXXXXXX)` / `(umask 077 && mkdir $tmp)`
    temp-directory idioms of autoconf into a `drwx--S---` directory that cannot
    be written to.  `config.status` then fails on every write ("Permission
    denied" on ./confXXXXXX/*), no Makefile/config.h is produced, and the build
    dies with "make: *** No targets specified and no makefile found".

    Dropping `umask 077` (the subshell stays) keeps the temp dir usable and is
    the fix already used by 80+ archives in this repository.  `configure` /
    `config.guess` are generated files shipped inside the pinned tarball, so
    they are edited in place here rather than through patches/ (same rationale
    as the abiword and 4ti2 recipes).
    """
    patched = 0
    for folder in dict.fromkeys((conanfile.build_folder, conanfile.source_folder)):
        for name in ("configure", "config.guess", "config.sub"):
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue
            # Byte-level read/write: the scripts are ASCII, but a text round-trip
            # with errors="ignore" could silently drop bytes.
            with open(path, "rb") as fh:
                data = fh.read()
            count = data.count(b"(umask 077 && ")
            if not count:
                continue
            with open(path, "wb") as fh:
                fh.write(data.replace(b"(umask 077 && ", b"("))
            patched += count
            conanfile.output.info(
                f"OHOS E114: removed 'umask 077' from {count} temp-dir site(s) in {path}")
    if not patched:
        conanfile.output.warn(
            "OHOS E114: no '(umask 077 && ' temp-dir pattern found in "
            "configure/config.guess. If the build fails with 'Permission denied' "
            "on ./confXXXXXX the upstream scripts changed and this workaround "
            "needs updating.")


class MmConan(ConanFile):
    name = "mm"
    version = "1.4.2"
    description = "OSSP mm — a shared memory allocation library (libmm)"
    license = "BSD-4-Clause"
    homepage = "http://www.ossp.org/pkg/lib/mm/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mm is supported only on Linux/OHOS")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # The 2006-era generated Makefile has no VPATH/$(srcdir) support, so the
        # project must be built in-source (same convention as advancescan/abduco).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # The bundled config.guess (2005-12-13) predates HarmonyOS' uname output,
            # so the build/host triplets must be supplied explicitly (knowledge base E002).
            # Derive the machine part from settings.arch instead of hard-coding aarch64.
            machine = {"armv8": "aarch64", "armv7": "arm",
                       "x86_64": "x86_64", "x86": "i686"}.get(str(self.settings.arch),
                                                               str(self.settings.arch))
            triplet = f"{machine}-unknown-linux-gnu"
            tc.configure_args.extend([f"--build={triplet}", f"--host={triplet}"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            # E114: must run before configure(), which generates config.status.
            _drop_umask_077(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # The upstream regression suite (mm_test) is part of the build contract.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Conan 2's copy() has no delete= argument; drop libtool *.la wrappers manually.
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["mm"]
        self.cpp_info.system_libs = ["m"]
