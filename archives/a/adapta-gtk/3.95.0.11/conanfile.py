#!/usr/bin/env python3
"""Conan recipe — adapta-gtk 3.95.0.11 (GTK theme data package).

Platform library name "adapta-gtk" maps to the upstream project
adapta-project/adapta-gtk-theme (the same family as the Arch package
adapta-gtk-theme), tag 3.95.0.11.

This is a pure data/theme package: it installs the four compiled GTK
theme variants (Adapta, Adapta-Nokto, Adapta-Eta, Adapta-Nokto-Eta —
the theme identifiers are upstream names and must keep the exact
directory names so GTK can resolve them via index.theme) under
share/themes/ plus the GPL-2.0 and CC-BY-SA-4.0 licenses.

Upstream ships this theme as SCSS/SVG sources that are compiled at
build time with sassc (SCSS→CSS) and inkscape (SVG→PNG asset
rendering). Neither tool is available on the OHOS build host (no conan
recipe, no cmd-pkgs prebuilt, pip libsass wheel fails to build for the
OHOS clang), so — following the adw-gtk 6.5 / adw-gtk3 6.5 theme data
package precedent in this repository — the compiled theme data is
taken from a distribution package built from the exact same upstream
tag 3.95.0.11.

Data source (CI #18008 fix): the FreeBSD official binary package
`adapta-gtk-theme-3.95.0.11_5.pkg` (pkg.freebsd.org quarterly
repository, built with sassc+inkscape from upstream tag 3.95.0.11).
It is a plain xz-compressed tar archive, so it is decompressed with
the Python standard-library `tarfile` module — no third-party native
extension is required. (The previous Arch Linux .tar.zst source
required the `zstandard` module, whose native .so is rejected by the
OHOS code-signature check on CI workers.) Content of the four theme
variants and both licenses is byte-identical to the upstream-compiled
data (verified SHA256 of index.theme / gtk.css / gtk.gresource /
GPLv2 / CC-BY-SA-4.0). Licenses are also fetched separately from the
official upstream repository tag 3.95.0.11.
"""
import os
import tarfile

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, download
from conan.tools.layout import basic_layout


class AdaptaGtkConan(ConanFile):
    name = "adapta-gtk"
    version = "3.95.0.11"
    description = "An adaptive Gtk+ theme based on Material Design Guidelines"
    license = "GPL-2.0 AND CC-BY-SA-4.0"
    homepage = "https://github.com/adapta-project/adapta-gtk-theme"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        theme = self.conan_data["sources"]["theme"]
        download(self, url=theme["url"], filename="theme.pkg", sha256=theme["sha256"])

        # The FreeBSD package is an xz-compressed tar archive. The Python
        # standard library tarfile module handles "r:xz" natively, so no
        # third-party native extension (zstandard) is needed on the OHOS
        # build host. Paths look like /usr/local/share/themes/<variant>/...
        with tarfile.open("theme.pkg", "r:xz") as tf:
            for member in tf:
                if member.isdir() or member.islnk() or member.issym():
                    continue
                name = member.name.lstrip("/")
                if not name.startswith("usr/local/share/themes/"):
                    continue
                # strip the leading "usr/local/" so we land on share/themes/
                rel = name[len("usr/local/"):]
                target = os.path.join(self.source_folder, rel)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with tf.extractfile(member) as src, open(target, "wb") as dst:
                    dst.write(src.read())

        # Licenses from the official upstream repo tag (SHA256 verified).
        for key, fname in (("license_copying", "COPYING"),
                           ("license_ccbysa4", "LICENSE_CC_BY_SA4")):
            lic = self.conan_data["sources"][key]
            download(self, url=lic["url"], filename=fname, sha256=lic["sha256"])

    def build(self):
        # Theme data package: files are pre-built by upstream tooling
        # (sassc + inkscape) for the exact same upstream tag; no
        # compilation is needed on the OHOS host.
        apply_conandata_patches(self)
        pass

    def package(self):
        themes_src = os.path.join(self.source_folder, "share", "themes")
        themes_dst = os.path.join(self.package_folder, "share", "themes")
        for variant in ("Adapta", "Adapta-Nokto", "Adapta-Eta", "Adapta-Nokto-Eta"):
            src = os.path.join(themes_src, variant)
            dst = os.path.join(themes_dst, variant)
            if os.path.isdir(src):
                os.makedirs(dst, exist_ok=True)
                for root, _dirs, files in os.walk(src):
                    for fname in files:
                        fsrc = os.path.join(root, fname)
                        frel = os.path.relpath(fsrc, src)
                        fdst = os.path.join(dst, frel)
                        os.makedirs(os.path.dirname(fdst), exist_ok=True)
                        with open(fsrc, "rb") as fi, open(fdst, "wb") as fo:
                            fo.write(fi.read())
        # Licenses
        lic_dir = os.path.join(self.package_folder, "share", "licenses", "adapta-gtk")
        os.makedirs(lic_dir, exist_ok=True)
        for fname in ("COPYING", "LICENSE_CC_BY_SA4"):
            fsrc = os.path.join(self.source_folder, fname)
            if os.path.isfile(fsrc):
                with open(fsrc, "rb") as fi, open(os.path.join(lic_dir, fname), "wb") as fo:
                    fo.write(fi.read())

    def package_info(self):
        # Theme data package: no cpp_info (no libs/headers/binaries).
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
