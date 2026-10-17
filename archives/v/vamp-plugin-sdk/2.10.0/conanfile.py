#!/usr/bin/env python3
"""Conan recipe for vamp-plugin-sdk 2.10.0 (Autotools build)."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class VampPluginSdkConan(ConanFile):
    name = "vamp-plugin-sdk"
    version = "2.10.0"
    description = "An API for audio analysis and feature extraction plugins (plugin and host SDK)"
    license = "BSD-3-Clause"
    homepage = "https://vamp-plugins.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        # In-tree Autotools build: upstream configure generates Makefile with
        # paths relative to the source root.  Using basic_layout here put the
        # build in a detached build-release/ folder and made `make` lose the
        # header prerequisites, so build directly in the source folder.
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = os.path.join("build", "conan-generators")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _sign_ohos_elf(self, path):
        tools = {}
        for name in ("llvm-readelf", "llvm-objcopy", "binary-sign-tool"):
            tools[name] = shutil.which(name) or os.path.join("/data/service/hnp/bin", name)
            if not os.path.isfile(tools[name]):
                raise ConanException(f"Required OHOS tool is missing: {name}")
        temporary = path + ".vamp-signed"
        subprocess.run(
            [tools["binary-sign-tool"], "sign", "-inFile", path,
             "-outFile", temporary, "-selfSign", "1"], check=True, timeout=60
        )
        sections = subprocess.run(
            [tools["llvm-readelf"], "-SW", temporary], check=True,
            capture_output=True, text=True, timeout=30
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"Signed ELF has invalid .codesign count: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Core SDK only: keep the optional simple-host / libsndfile chain
        # explicitly disabled (R36 / optional-dependency rule).  The SDK
        # libraries (libvamp-sdk, libvamp-hostsdk) have no third-party deps.
        # Upstream Makefile always builds both static and shared SDK libs, so
        # no --enable/--disable-shared flags are passed here.
        tc.configure_args.append("--disable-programs")
        tc.generate()

    def build(self):
        # OHOS/HMDFS constraint (§3.4 non-chmod path): autoconf's config.status
        # runs `umask 077 && mktemp -d` which creates a 0700 temp dir owned by
        # the storage owner; our effective uid cannot write inside it.  Provide
        # a mktemp shim that resets umask to 002 so the temp dir is
        # group-writable, and prepend it to PATH for this build.
        shim_dir = os.path.join(self.build_folder, "shim")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "mktemp")
        with open(shim, "w") as f:
            f.write("#!/bin/sh\numask 002\nexec /bin/mktemp \"$@\"\n")
        os.chmod(shim, 0o755)
        os.environ["PATH"] = shim_dir + os.pathsep + os.environ.get("PATH", "")

        autotools = Autotools(self)
        autotools.configure()
        apply_conandata_patches(self)
        # Build the SDK libraries only (static + shared); upstream `make
        # install` unconditionally requires the libsndfile-dependent simple
        # host, so we mirror the install target manually in package().
        # -j1: OHOS SELinux rejects make jobserver mkfifo (Operation not
        # permitted), so parallel make is not usable here.
        self.run("make sdk -j1", env="conanbuild")

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        libdir = os.path.join(pkg, "lib")
        incdir = os.path.join(pkg, "include")

        # Mirror upstream Makefile.in `install` target for the SDK subset
        # (headers, static libs, shared libs + ABI/dev symlinks, pkgconfig).
        # The simple host / RDF generator / example plugins are not packaged
        # because --disable-programs disables them.
        for hdr in ("vamp", "vamp-sdk", "vamp-hostsdk"):
            shutil.copytree(os.path.join(src, hdr),
                            os.path.join(incdir, hdr))
        os.makedirs(libdir, exist_ok=True)

        # Static libraries (always built by upstream)
        shutil.copy(os.path.join(src, "libvamp-sdk.a"), libdir)
        shutil.copy(os.path.join(src, "libvamp-hostsdk.a"), libdir)

        if self.options.shared:
            # Shared libraries: upstream install names
            #   libvamp-sdk.so.2.10.0      (soname libvamp-sdk.so.2, dev link libvamp-sdk.so)
            #   libvamp-hostsdk.so.3.10.0  (soname libvamp-hostsdk.so.3, dev link libvamp-hostsdk.so)
            real_files = {
                "libvamp-sdk.so.2.10.0": "libvamp-sdk.so",
                "libvamp-hostsdk.so.3.10.0": "libvamp-hostsdk.so",
            }
            for real, built in real_files.items():
                shutil.copy(os.path.join(src, built), os.path.join(libdir, real))
            for name, soname, dev in (
                ("libvamp-sdk.so.2.10.0", "libvamp-sdk.so.2", "libvamp-sdk.so"),
                ("libvamp-hostsdk.so.3.10.0", "libvamp-hostsdk.so.3", "libvamp-hostsdk.so"),
            ):
                for link in (soname, dev):
                    # HMDFS does not support overwriting symlinks via `ln -sf`:
                    # remove first, then create (R5 / OHOS constraint).
                    link_path = os.path.join(libdir, link)
                    if os.path.lexists(link_path):
                        os.unlink(link_path)
                    os.symlink(name, link_path)

        # pkgconfig files (upstream runs sed %PREFIX% -> INSTALL_PREFIX)
        pcdir = os.path.join(libdir, "pkgconfig")
        os.makedirs(pcdir, exist_ok=True)
        for pc in ("vamp.pc", "vamp-sdk.pc", "vamp-hostsdk.pc"):
            with open(os.path.join(src, "pkgconfig", pc + ".in")) as fin:
                content = fin.read().replace("%PREFIX%", self.package_folder)
            with open(os.path.join(pcdir, pc), "w") as fout:
                fout.write(content)

        # Sign the real shared-library files (not the dev symlinks) for OHOS
        # runtime; static-only builds have no ELF to sign.
        if str(self.settings.os) == "OHOS" and self.options.shared:
            for real in ("libvamp-sdk.so.2.10.0", "libvamp-hostsdk.so.3.10.0"):
                lib_path = os.path.join(libdir, real)
                if os.path.exists(lib_path):
                    self._sign_ohos_elf(lib_path)

    def package_info(self):
        self.cpp_info.libs = ["vamp-hostsdk", "vamp-sdk"]
        self.cpp_info.set_property("pkg_config_name", "vamp")
        # R08: add lib dir to LD_LIBRARY_PATH so test_package and downstream
        # consumers can find the shared libraries at runtime.
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
