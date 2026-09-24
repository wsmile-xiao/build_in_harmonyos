#!/usr/bin/env python3
"""Conan recipe — fcgi2 2.4.7

FastCGI 2.x: the reference FastCGI C/C++ library (libfcgi, libfcgi++)
plus the cgi-fcgi tool. GitHub archive ships no configure: autoreconf
bootstrap required (cliquer-style), automake/libtool via tool_requires.
License: FastCGI (Open Market "TCP Transparency" license, LICENSE).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Fcgi2Conan(ConanFile):
    name = "fcgi2"
    version = "2.4.7"
    description = "FastCGI 2.x - reference FastCGI C/C++ library (libfcgi, libfcgi++) and cgi-fcgi tool"
    license = "FastCGI"
    homepage = "https://github.com/FastCGI-Archives/fcgi2"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # CI worker 镜像缺 automake/libtoolize；GitHub archive 无 configure 必须自举
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        # multi-URL fallback: mirrors injected by the W3 pre-download flow may
        # be unreachable; codeload serves the identical archive (same sha256)
        urls = self.conan_data["sources"].get("url")
        sha = self.conan_data["sources"]["sha256"]
        candidates = list(urls) if isinstance(urls, list) else [urls]
        candidates.append(
            "https://codeload.github.com/FastCGI-Archives/fcgi2/tar.gz/refs/tags/2.4.7")
        last_err = None
        for u in candidates:
            try:
                fname = "fcgi2-2.4.7.tar.gz" if "codeload" in u else None
                if fname:
                    get(self, u, sha256=sha, strip_root=True, filename=fname)
                else:
                    get(self, u, sha256=sha, strip_root=True)
                return
            except Exception as e:
                self.output.info(f"source download failed from {u}: {e}")
                last_err = e
        raise last_err

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 2007-era config.guess/sub can't guess on OHOS and reject new triplets:
        # force build triplet to skip guessing (jwhois-style precedent)
        if self.settings.os == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("GitHub archive has no configure: autoreconf bootstrap")
            autotools.autoreconf(build_script_folder=self.source_folder)
        # E011: umask 077 fix must come AFTER autoreconf (bootstrap regenerates
        # configure), gsl/cliquer-style
        import glob
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            with open(_cfg, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # drop libtool .la files (baked absolute libdir paths)
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for fn in os.listdir(libdir):
                if fn.endswith(".la"):
                    os.unlink(os.path.join(libdir, fn))

    def package_info(self):
        self.cpp_info.libs = ["fcgi++", "fcgi"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
