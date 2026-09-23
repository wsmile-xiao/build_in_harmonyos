import os
import shutil
import ssl
import urllib.request

from conan import ConanFile
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches,
    check_sha256, unzip
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class ThttpdConan(ConanFile):
    name = "thttpd"
    version = "2.29"
    description = "thttpd - tiny/turbo/throttling HTTP server"
    license = "BSD-2-Clause"
    homepage = "https://acme.com/software/thttpd/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception as e:
            # Fallback for servers with legacy TLS: acme.com only negotiates
            # TLSv1.0-era cipher suites, which Python's OpenSSL rejects at the
            # default security level (SSLV3_ALERT_HANDSHAKE_FAILURE). Retry
            # with a relaxed SSL context; archive integrity is still
            # guaranteed by the sha256 check against conandata.yml.
            self.output.warning(f"Conan get() failed ({e}); "
                                f"retrying with relaxed SSL context")
            url = self.conan_data["sources"]["url"]
            sha256 = self.conan_data["sources"]["sha256"]
            filename = url.rsplit("/", 1)[-1]
            filepath = os.path.join(self.source_folder, filename)
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            ctx.set_ciphers("DEFAULT@SECLEVEL=0")
            ctx.minimum_version = ssl.TLSVersion.TLSv1
            with urllib.request.urlopen(url, timeout=120, context=ctx) as resp, \
                    open(filepath, "wb") as f:
                shutil.copyfileobj(resp, f)
            check_sha256(self, filepath, sha256)
            unzip(self, filepath, self.source_folder, strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        # thttpd uses autoconf 2.13 which does not support out-of-source builds.
        # Run configure and make in the source directory.
        apply_conandata_patches(self)
        self.run(f"./configure --prefix={self.package_folder}", env="conanbuild", cwd=self.source_folder)
        self.run("make -j1", env="conanbuild", cwd=self.source_folder)

    def package(self):
        # Create directories that old Makefile install expects to exist
        for d in ["sbin", "man/man1", "man/man8", "www/cgi-bin"]:
            os.makedirs(os.path.join(self.package_folder, d), exist_ok=True)
        self.run("make install", env="conanbuild", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["sbin"]
