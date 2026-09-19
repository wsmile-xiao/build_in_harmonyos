#!/usr/bin/env python3
"""Conan recipe for libamrnb 11.0.0.0 (Autotools).

libamrnb packages the 3GPP TS 26.104 (AMR speech codec, floating-point
ANSI-C reference implementation, Release 11) behind a small autotools
wrapper by Stanislav Brabec (penguin.cz/~utx/amr).

The upstream tarball only contains the wrapper (configure + 3 portability
patches + a prepare script).  The 3GPP archive 26104-b00.zip must sit next
to the wrapper before `make` runs; the Makefile then unpacks it, applies
the patches and renames the interfaces itself (prepare_sources.sh, same
flow as the FreeBSD audio/libamrnb port).  Both archives are declared in
conandata.yml.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibamrnbConan(ConanFile):
    name = "libamrnb"
    version = "11.0.0.0"
    description = "3GPP TS 26.104 AMR-NB speech codec (floating-point reference implementation) library and tools"
    license = "BSD-3-Clause AND 3GPP"
    homepage = "http://www.penguin.cz/~utx/amr"
    url = ""

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libamrnb is supported only on Linux/OHOS")
        if self.settings.arch != "armv8" and self.settings.os == "OHOS":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = self.conan_data["sources"][self.version]
        # [0] wrapper tarball -> extract (single top-level dir)
        get(self, **sources[0], strip_root=True)
        # [1] 3GPP TS 26.104 v11.0.0 source zip -> keep packed next to the
        # wrapper; the upstream Makefile unpacks + patches it during build
        download(self, sources[1]["url"], "26104-b00.zip",
                 sha256=sources[1]["sha256"])

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Upstream config.guess/config.sub (2012) do not recognise the
        # aarch64-linux-ohos triplet.  Use the generic linux-gnu triplet;
        # libamrnb is plain C89 with no OS-specific code paths (celt/a52dec
        # precedent).
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()

    def build(self):
        # E011/E114: remove umask 077 from the configure temp-dir creation
        # before anything else runs (HMDFS setgid makes the confXXXXXX dir
        # unwritable, breaking config.status at subs1.awk).
        apply_conandata_patches(self)
        # The upstream Makefile regenerates the 3GPP sources into
        # $(top_srcdir) (unpack 26104-b00.zip, apply patches, sed-rename
        # interfaces).  Copy the pristine source tree (wrapper + zip) into
        # the build folder and build in-tree so the source cache stays
        # clean and the generated files live in a disposable copy.
        copy(self, "*", self.source_folder, self.build_folder)
        zip_path = os.path.join(self.build_folder, "26104-b00.zip")
        if not os.path.isfile(zip_path) or os.path.getsize(zip_path) != 427897:
            raise ConanException(
                "26104-b00.zip missing or wrong size at %s (expected 427897 bytes; "
                "a ~35KB HTML file indicates the 3gpp.org WAF served its block "
                "page instead of the archive)" % zip_path)
        autotools = Autotools(self)
        autotools.configure()
        # prepare_sources.sh (host tools: bash/patch/sed/tr/unzip) runs as
        # part of make; -j1 because the source-prep chain is a single
        # serialization point upstream.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Conan 2 copy() has no delete= argument; remove libtool *.la
        # wrappers manually (a52dec precedent).
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        # Headers install to include/amrnb/ -> consumers use
        # #include <amrnb/interf_enc.h> etc.
        self.cpp_info.libs = ["amrnb"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.includedirs = ["include", "include/amrnb"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
