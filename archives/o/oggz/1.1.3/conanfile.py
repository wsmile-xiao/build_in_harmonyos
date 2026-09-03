#!/usr/bin/env python3
"""Conan recipe for oggz 1.1.3 (liboggz library + oggz CLI toolset).

Build system: Autotools (configure + make)
Dependency:   libogg/1.3.6.1 -- system-name library, consumed statically (R26)
Products:     liboggz static/shared library + oggz CLI tools (bin/)
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    download,
    export_conandata_patches,
    replace_in_file,
    rm,
)
from conan.tools.env import Environment
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class OggzConan(ConanFile):
    name = "oggz"
    version = "1.1.3"
    description = "High-level C API for Ogg stream parsing/generation + oggz CLI tools"
    license = "BSD-3-Clause"
    homepage = "https://www.xiph.org/oggz/"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # R26: libogg is a system-name library -> force static consumption.
    default_options = {"shared": False, "fPIC": True, "libogg/*:shared": False}

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

    def requirements(self):
        self.requires("libogg/1.3.6.1")

    def source(self):
        # Manual tar extraction: conan's get(strip_root=True) hits an HMDFS quirk
        # on this tarball's top-level "PATCHES" file (IsADirectoryError), so we
        # extract with plain tarfile and flatten the single "liboggz-1.1.3/" dir.
        import os
        import tarfile

        src = self.conan_data["sources"][self.version]
        filename = "liboggz-1.1.3.tar.gz"
        download(self, src["url"], filename, sha256=src["sha256"])
        root = "liboggz-1.1.3"
        with tarfile.open(filename, "r:gz") as tar:
            members = []
            for m in tar.getmembers():
                name = m.name.replace("\\", "/")
                if name == root:
                    if m.isdir():
                        continue  # drop the single top-level directory entry
                    raise ConanException("unexpected archive member: %s" % name)
                if not name.startswith(root + "/"):
                    raise ConanException("unexpected archive member: %s" % name)
                if name == root + "/PATCHES":
                    # Upstream changelog file "PATCHES" case-insensitively
                    # collides with the exported lowercase "patches/" dir on the
                    # OHOS sandbox filesystem (EISDIR). Not needed to build.
                    continue
                m.name = name[len(root) + 1:]
                m.path = m.name
                if m.linkpath and m.linkpath.startswith(root + "/"):
                    m.linkpath = m.linkpath[len(root) + 1:]
                    m.linkname = m.linkpath
                members.append(m)
            tar.extractall(self.source_folder, members=members)
        os.unlink(os.path.join(self.source_folder, filename))
        # OHOS platform patches: HarmonyOS triplet support in config.guess/config.sub
        apply_conandata_patches(self)

    def generate(self):
        # oggz configure.ac probes libogg via PKG_CHECK_MODULES(OGG, ogg >= 1.0)
        pkgconfig = PkgConfigDeps(self)
        pkgconfig.set_property("libogg", "pkg_config_name", "ogg")
        pkgconfig.generate()

        # AutotoolsToolchain maps options.shared -> --enable-static/--disable-shared.
        # libogg itself is always consumed statically (R26, default_options above).
        tc = AutotoolsToolchain(self)
        tc.generate()

    @staticmethod
    def _ohos_tool(name):
        path = shutil.which(name) or os.path.join("/data/service/hnp/bin", name)
        if not os.path.isfile(path):
            raise ConanException("Required OHOS tool is missing: %s" % name)
        return path

    @staticmethod
    def _is_elf(path):
        with open(path, "rb") as fh:
            return fh.read(4) == b"\x7fELF"

    def _sign_ohos_elf(self, path):
        """Add a self-signed .codesign section so the OHOS XPM loader accepts the ELF."""
        objcopy = self._ohos_tool("llvm-objcopy")
        readelf = self._ohos_tool("llvm-readelf")
        signer = self._ohos_tool("binary-sign-tool")
        sections = subprocess.run(
            [readelf, "-SW", path], check=True, capture_output=True,
            text=True, timeout=30,
        ).stdout
        count = sections.count(".codesign")
        if count == 1:
            self.output.info("Preserving existing .codesign section: %s" % path)
            return
        if count != 0:
            raise ConanException("ELF has invalid .codesign count: %s" % path)
        clean = path + ".sign-clean"
        signed = path + ".oggz-signed"
        try:
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", path, clean],
                check=True, timeout=30,
            )
            subprocess.run(
                [signer, "sign", "-inFile", clean, "-outFile", signed, "-selfSign", "1"],
                check=True, timeout=60,
            )
            sections = subprocess.run(
                [readelf, "-SW", signed], check=True, capture_output=True,
                text=True, timeout=30,
            ).stdout
            if sections.count(".codesign") != 1:
                raise ConanException("Signed ELF has invalid .codesign count: %s" % path)
            os.chmod(signed, (os.stat(path).st_mode & 0o777) | 0o055)
            os.replace(signed, path)
        finally:
            for generated in (clean, signed):
                if os.path.exists(generated):
                    os.remove(generated)

    def build(self):
        # Configure temp-dir fix (mktemp -> mkdir on OHOS HMDFS, E002) is carried
        # by patches/0003-configure.patch, applied in source().
        configure = os.path.join(self.source_folder, "configure")
        autotools = Autotools(self)
        configure_args = autotools._configure_args or ""
        if str(self.settings.os) == "OHOS":
            # Coreutils shims under $DEFAULT_PREFIX/bin break configure's
            # heredocs/pipes (cat/sort/sed) when they win PATH (E540). Drive
            # configure/make with a controlled environment via subprocess so the
            # profile buildenv PATH (re-injected by conan's self.run) is bypassed.
            env = self._ohos_build_env()
            subprocess.run(
                '"%s" %s' % (configure, configure_args),
                cwd=self.build_folder, env=env, shell=True, check=True,
            )
            subprocess.run(
                "make -j1", cwd=self.build_folder, env=env, shell=True, check=True
            )
        else:
            autotools.configure()
            autotools.make(args=["-j1"])

    def package(self):
        if str(self.settings.os) == "OHOS":
            env = self._ohos_build_env()
            env["DESTDIR"] = self.package_folder
            subprocess.run(
                "make install -j1", cwd=self.build_folder, env=env,
                shell=True, check=True,
            )
        else:
            autotools = Autotools(self)
            autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        # OHOS executables must carry a .codesign section (R38 tools / libs).
        if str(self.settings.os) == "OHOS" and can_run(self):
            bindir = os.path.join(self.package_folder, "bin")
            if os.path.isdir(bindir):
                for name in sorted(os.listdir(bindir)):
                    path = os.path.join(bindir, name)
                    if os.path.isfile(path) and not os.path.islink(path) and self._is_elf(path):
                        self._sign_ohos_elf(path)
            if self.options.shared:
                libdir = os.path.join(self.package_folder, "lib")
                for name in sorted(os.listdir(libdir)):
                    path = os.path.join(libdir, name)
                    if os.path.isfile(path) and not os.path.islink(path) and name.startswith("liboggz.so"):
                        self._sign_ohos_elf(path)

    def _ohos_build_env(self):
        """Controlled environment for configure/make on OHOS.

        The $DEFAULT_PREFIX/bin coreutils shims installed by previous adapters
        break autotools heredocs/pipes (cat/sort) once they win the PATH lookup,
        and conan re-injects the profile buildenv PATH around every self.run().
        Returning a plain os.environ copy with the system coreutils first keeps
        configure/make healthy without losing the toolchain-provided variables.
        """
        env = dict(os.environ)
        env["PATH"] = (
            "/system/bin:/usr/bin:/bin:/data/service/hnp/bin:"
            "/storage/Users/currentUser/usr/local/bin"
        )
        env["CONFIG_SHELL"] = "/system/bin/sh"
        env["SHELL"] = "/system/bin/sh"
        env["MKDIR_P"] = "/system/bin/mkdir -p"
        env["CC"] = "/data/service/hnp/bin/clang"
        env["CFLAGS"] = "-fPIC -O2 -O3"
        env["PKG_CONFIG_PATH"] = self.generators_folder
        return env

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "oggz")
        comp = self.cpp_info.components["oggz"]
        comp.libs = ["oggz"]
        comp.requires = ["libogg::libogg"]
        comp.set_property("cmake_target_name", "oggz::oggz")
        comp.set_property("pkg_config_name", "oggz")
