"""Conan recipe for libsigrokdecode 0.5.3 on HarmonyOS PC."""

import os
import glob
import shutil
import subprocess
import re
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, replace_in_file, save)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibsigrokdecodeConan(ConanFile):
    name = "libsigrokdecode"
    version = "0.5.3"
    package_type = "library"
    description = "Protocol decoder library for the sigrok logic analyzer suite"
    homepage = "https://sigrok.org/wiki/Libsigrokdecode"
    license = "GPL-3.0-or-later"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        self.requires("glib/2.88.3.1")
        # GLib and Python publish against distinct zlib revisions. Keep the
        # embedded interpreter's published private graph rather than forcing
        # either dependency to a binary revision that does not exist.
        # The shared object embeds libpython at runtime. This private graph
        # must retain Python's binary for downstream consumers as well.
        self.requires("python/3.12.9.1", visible=False, no_skip=True)

    def build_requirements(self):
        self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("LIBSIGROKDECODE_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("local source archive is not a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        python_root = self.dependencies["python"].package_folder
        # Upstream 0.5.3 only probes python-3.8-embed. Keep the embedded
        # interpreter, headers and libpython in one Conan dependency closure.
        save(self, os.path.join(self.generators_folder, "python-3.12-embed.pc"),
             "prefix={}\n"
             "libdir=${{prefix}}/lib\n"
             "includedir=${{prefix}}/include/python3.12\n"
             "Name: python-3.12-embed\n"
             "Description: Python 3.12 embedding library\n"
             "Version: 3.12.9\n"
             "Libs: -L${{libdir}} -lpython3.12\n"
             "Cflags: -I${{includedir}}\n".format(python_root))
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # This release's config.guess cannot classify HarmonyOS uname.
            tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.configure_args.extend([
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if self.options.shared else "--enable-static",
        ])
        tc.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    @staticmethod
    def _sign_elf(path):
        signer = shutil.which("binary-sign-tool")
        if not signer:
            raise ConanInvalidConfiguration("binary-sign-tool is required on OHOS")
        pending = path + ".sigrokdecode-signing"
        signed = path + ".sigrokdecode-signed"
        if os.path.exists(pending) or os.path.exists(signed):
            raise ConanInvalidConfiguration("stale signing sibling: {}".format(path))
        try:
            shutil.copy2(path, pending)
            subprocess.run([signer, "sign", "-inFile", pending,
                            "-outFile", signed, "-selfSign", "1"],
                           check=True, capture_output=True, text=True, timeout=40)
            os.chmod(signed, os.stat(path).st_mode)
            os.replace(signed, path)
        finally:
            for temporary in (pending, signed):
                if os.path.exists(temporary):
                    os.unlink(temporary)

    def build(self):
        # Patch only the shipped configure script. Touching configure.ac
        # causes make to invoke aclocal-1.16/automake despite generated
        # Autotools inputs already being present in the release tarball.
        configure_path = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure_path,
                        "python-3.8-embed", "python-3.12-embed")
        if str(self.settings.os) == "OHOS":
            # On HMDFS, config.status can lose access to the confXXXXXX
            # directory made under umask 077. Limit the change to its two
            # directory-creation paths; do not relax unrelated file masks.
            replacements = (
                ('(umask 077 && mktemp -d "./confXXXXXX")',
                 '(umask 022 && mktemp -d "./confXXXXXX")'),
                ('(umask 077 && mkdir "$tmp")',
                 '(umask 022 && mkdir "$tmp")'),
            )
            with open(configure_path, encoding="utf-8") as stream:
                configure_text = stream.read()
            for old, new in replacements:
                if configure_text.count(old) != 1:
                    raise ConanException("unexpected Autoconf temp-dir pattern: {}".format(old))
                replace_in_file(self, configure_path, old, new)
        autotools = Autotools(self)
        python_exe = os.path.join(self.dependencies["python"].package_folder,
                                  "bin", "python3")
        autotools.configure(args=["PYTHON3={}".format(python_exe)])
        autotools.make(args=["-j1"])
        autotools.make(target="tests/main", args=["-j1"])
        if str(self.settings.os) == "OHOS":
            for path in glob.glob(os.path.join(self.build_folder, ".libs", "libsigrokdecode.so*")):
                if os.path.isfile(path) and not os.path.islink(path):
                    self._sign_elf(path)
            self._sign_elf(os.path.join(self.build_folder, "tests", ".libs", "main"))
        # Check is an explicit test requirement: do not silently turn off the
        # upstream suite when its pkg-config module is unavailable.
        env = Environment()
        env.define("PYTHONHOME", self.dependencies["python"].package_folder)
        # Autotools.make() activates the build environment, not Conan's run
        # environment. The Check binary needs the host/test graph's signed
        # shared libraries during the complete upstream suite.
        check_tmp = os.path.join(self.build_folder, ".check-tmp")
        os.makedirs(check_tmp, mode=0o700, exist_ok=True)
        # Check 0.15.2 tests TEMP before TMPDIR (and P_tmpdir may be /tmp,
        # which is read-only on HarmonyOS PC).
        env.define("TEMP", check_tmp)
        env.define("TMPDIR", check_tmp)
        for dependency in self.dependencies.values():
            folder = dependency.package_folder
            if folder:
                libdir = os.path.join(folder, "lib")
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        with env.vars(self).apply():
            autotools.make(target="check", args=["-j1"])
        check_log = os.path.join(self.build_folder, "tests", "main.log")
        if not os.path.isfile(check_log):
            raise ConanException("upstream Check log is missing: {}".format(check_log))
        with open(check_log, encoding="utf-8", errors="replace") as stream:
            result = stream.read()
        if not re.search(r"100%:\s*Checks:\s*39,\s*Failures:\s*0,\s*Errors:\s*0", result):
            raise ConanException("upstream Check suite did not report 39/39")
        self.output.info("UPSTREAM_39_OF_39_PASS")

    def package(self):
        # make install runs the packaged Python to copy decoder modules.
        # Give that subprocess the same runtime libraries as make check.
        env = Environment()
        env.define("PYTHONHOME", self.dependencies["python"].package_folder)
        for dependency in self.dependencies.values():
            folder = dependency.package_folder
            if folder:
                libdir = os.path.join(folder, "lib")
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        with env.vars(self).apply():
            Autotools(self).install()
        if str(self.settings.os) == "OHOS":
            for path in glob.glob(os.path.join(self.package_folder, "lib", "libsigrokdecode.so*")):
                if os.path.isfile(path) and not os.path.islink(path):
                    self._sign_elf(path)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["sigrokdecode"]
        self.cpp_info.set_property("pkg_config_name", "libsigrokdecode")
        self.runenv_info.define(
            "SIGROKDECODE_DIR",
            os.path.join(self.package_folder, "share", "libsigrokdecode", "decoders"),
        )
        self.runenv_info.define("PYTHONHOME", self.dependencies["python"].package_folder)
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.dependencies["python"].package_folder, "lib"))
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
