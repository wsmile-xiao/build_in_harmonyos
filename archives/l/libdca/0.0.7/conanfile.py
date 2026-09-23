#!/usr/bin/env python3
"""Conan recipe for the libdca DTS audio decoder."""
import glob
import os
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibdcaConan(ConanFile):
    name = "libdca"
    version = "0.0.7"
    description = "DTS Coherent Acoustics audio decoder library"
    license = "GPL-2.0-or-later"
    homepage = "https://www.videolan.org/developers/libdca.html"
    url = "https://code.videolan.org/videolan/libdca"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        # The bootstrap patch is stored as base64 text (.b64): its plain-text
        # form is ~52k lines, which overflows the GitCode .diff endpoint used
        # by AI review and CI checkout (see Crypt-OpenSSL-RSA precedent).
        # conandata.yml declares the decoded name so apply_conandata_patches()
        # keeps working; here we export the .b64 decoded to that name.
        import base64
        b64_path = os.path.join(self.recipe_folder, "patches",
                                "0001-bootstrap-autotools.patch.b64")
        patch_path = os.path.join(self.export_sources_folder, "patches",
                                  "0001-bootstrap-autotools.patch")
        os.makedirs(os.path.dirname(patch_path), exist_ok=True)
        with open(b64_path, "r") as f:
            data = base64.b64decode(f.read())
        with open(patch_path, "wb") as f:
            f.write(data)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libdca is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        tc.configure_args.extend([
            "--disable-oss",
            "--disable-solaris-audio",
            "--disable-al-audio",
            "--disable-win",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # No autoreconf: CI workers lack automake/aclocal. The generated
        # configure/aclocal.m4/Makefile.in/.auto are vendored in
        # patches/0001-bootstrap-autotools.patch (see conandata.yml).
        # patch tooling does not preserve exec bits on rebuilt files, so
        # restore them explicitly.
        os.chmod(os.path.join(self.source_folder, "configure"), 0o755)
        aux_dir = os.path.join(self.source_folder, ".auto")
        if os.path.isdir(aux_dir):
            for aux in os.listdir(aux_dir):
                os.chmod(os.path.join(aux_dir, aux), 0o755)
        # Vendored Makefile.in files land in the source folder at patch time,
        # possibly older than the regenerated configure, which makes make fire
        # the automake "Makefile.in is out of date" rule and fail on CI
        # (no automake there). Bump Makefile.in mtimes so make treats them as
        # up to date.
        now = time.time()
        for mk in glob.glob(os.path.join(self.source_folder, "**", "Makefile.in"),
                            recursive=True):
            os.utime(mk, (now, now))
        if self.settings.os == "OHOS":
            # The generated configure creates its temp dir with "umask 077"
            # (AS_TMPDIR). On the OHOS host the HMDFS build uid is mapped to a
            # different owner, so mode-0700 dirs are unwritable and
            # config.status aborts with EACCES. Relax the umask to 022.
            configure_path = os.path.join(self.source_folder, "configure")
            if os.path.exists(configure_path):
                with open(configure_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if "umask 077" in content:
                    content = content.replace("umask 077", "umask 022")
                    with open(configure_path, "w", encoding="utf-8") as f:
                        f.write(content)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        check_args = ["-j1"]
        if self.settings.os == "OHOS":
            # HMDFS denies direct kernel exec of #!/bin/sh test scripts, so the
            # automake driver must run regression/compile through the configure
            # shell; both then skip (77) because their fixtures are unbundled.
            check_args.append("LOG_COMPILER=/bin/sh")
        autotools.make(target="check", args=check_args)

    def package(self):
        if self.settings.os == "OHOS":
            # HMDFS cannot create symlinks. Upstream src's install-data-hook
            # makes dtsdec.1/extract_dts.1 as ln -sf aliases of the real man
            # pages; copy the already-installed DESTDIR man page instead.
            makefile_path = os.path.join(self.build_folder, "src", "Makefile")
            if os.path.exists(makefile_path):
                with open(makefile_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                old_hook = (
                    'ln -sf "$(man1dir)/$${name}.1" '
                    '"$(DESTDIR)$(man1dir)/$${oldname}.1"'
                )
                new_hook = (
                    'cp -f "$(DESTDIR)$(man1dir)/$${name}.1" '
                    '"$(DESTDIR)$(man1dir)/$${oldname}.1"'
                )
                if old_hook in content:
                    with open(makefile_path, "w", encoding="utf-8") as f:
                        f.write(content.replace(old_hook, new_hook))
        autotools = Autotools(self)
        autotools.install()
        for wrapper in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(wrapper)

    def package_info(self):
        self.cpp_info.libs = ["dca"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
