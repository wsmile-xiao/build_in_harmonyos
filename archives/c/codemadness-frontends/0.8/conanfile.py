#!/usr/bin/env python3
"""Conan recipe — codemadness-frontends 0.8 (Makefile).

Experimental CLI/CGI/Gopher frontends for YouTube (idiotbox). Upstream
builds four youtube frontends (cgi, cli, feed, gopher) plus static helper
archives (libutil/libjson/libhttps/libxml). There is no `install` target,
so package() copies the built binaries into bin/ with youtube- prefixes.
TLS is provided by openssl (portability patch rewrites https.c from the
libtls client API to the OpenSSL client API with the same guarantees:
peer verification, hostname check and SNI).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CodemadnessFrontendsConan(ConanFile):
    name = "codemadness-frontends"
    version = "0.8"
    description = "Experimental CLI, CGI and Gopher frontends for YouTube"
    license = "ISC"
    homepage = "https://codemadness.org/idiotbox.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Upstream Makefile builds youtube CGI/CLI/Gopher/Feed binaries only;
    # there is no library (.a/.so) target.
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # openssl/3.5.8.1 ships a published static-only OHOS build and a
        # GitHub + gh-proxy source; libressl/3.9.1 is only hosted on
        # ftp/cdn.openbsd.org, whose 4.3MB tarball the build network
        # repeatedly truncates mid-download (IncompleteRead).
        self.requires("openssl/3.5.8.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        # The OHOS adjustments (Linux defines, TLS include/lib paths,
        # dynamic link instead of -static) are passed on the make command
        # line, which takes precedence over `=` assignments in the Makefile.
        # The libtls -> OpenSSL port lives in patches/ (applied below via
        # conandata, surfaced in build/ through the normal Conan flow).
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _resolve_cc(self):
        # Candidate C compilers in preference order. Every candidate is
        # verified to be an existing executable: a stale conf/ENV entry
        # (e.g. a clang path missing on the current worker) must not
        # shadow a working compiler later in the chain (make Error 127).
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        candidates = [
            compilers.get("c"),
            os.environ.get("CC"),
            shutil.which("clang"),
            shutil.which("cc"),
        ]
        for cand in candidates:
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        return "cc"

    def build(self):
        cc = self._resolve_cc()
        openssl_pkg = self.dependencies["openssl"].package_folder
        openssl_include = os.path.join(openssl_pkg, "include")
        openssl_lib = os.path.join(openssl_pkg, "lib")
        # Upstream Makefile defaults to the OpenBSD block; the Linux block
        # (with -D_DEFAULT_SOURCE -D_XOPEN_SOURCE=700) is commented out, so
        # pass the Linux defines explicitly. Override both LIBTLS link vars
        # to drop the upstream `-static` (bionic cannot static-link these).
        # -lssl/-lcrypto come from the static-only openssl package, so the
        # final link also needs -ldl -lpthread (mirrors openssl cpp_info).
        frontend_cflags = " ".join([
            "-I../",
            "-I.",
            "-D_DEFAULT_SOURCE",
            "-D_XOPEN_SOURCE=700",
            "-O2",
            "-fPIC",
            f"-I{openssl_include}",
        ])
        tls_link = f"-L{openssl_lib} -lssl -lcrypto -ldl -lpthread"
        # R9/E074: HMDFS jobserver FIFO breaks parallel make, use -j1.
        self.run(
            f'make -j1 CC="{cc}" FRONTENDS_CFLAGS="{frontend_cflags}" '
            f'FRONTENDS_CPPFLAGS="" FRONTENDS_LDFLAGS="-L{openssl_lib}" '
            f'LIBTLS_LDFLAGS="{tls_link}" LIBTLS_LDFLAGS_STATIC="{tls_link}"',
            cwd=self.source_folder,
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        renames = {
            "youtube/cli": "youtube-cli",
            "youtube/cgi": "youtube-cgi",
            "youtube/gopher": "youtube-gopher",
            "youtube/feed": "youtube-feed",
        }
        for src_rel, dst_name in renames.items():
            # The Makefile has no `install` target, so copy the built
            # binaries manually. In-source Makefile build: they live under
            # the source tree; fall back to the build folder if needed.
            src_abs = os.path.join(self.source_folder, src_rel)
            if not os.path.isfile(src_abs):
                alt = os.path.join(self.build_folder, src_rel)
                if os.path.isfile(alt):
                    src_abs = alt
            if not os.path.isfile(src_abs):
                raise FileNotFoundError(f"expected built binary missing: {src_rel}")
            shutil.copy2(src_abs, os.path.join(bindir, dst_name))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        if str(self.settings.os) == "OHOS":
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            if os.path.isfile(sign_tool) and os.path.isfile(objcopy):
                for dst_name in renames.values():
                    bin_path = os.path.join(bindir, dst_name)
                    if not os.path.isfile(bin_path):
                        continue
                    os.chmod(bin_path, 0o755)
                    self.run(f"{objcopy} --remove-section .codesign {bin_path} 2>/dev/null || true")
                    tmp_signed = bin_path + ".signed"
                    self.run(f"{sign_tool} sign -inFile {bin_path} -outFile {tmp_signed} -selfSign 1",
                             quiet=True)
                    os.replace(tmp_signed, bin_path)
                    os.chmod(bin_path, 0o755)

    def package_info(self):
        # Standalone binaries, no library to link against.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
