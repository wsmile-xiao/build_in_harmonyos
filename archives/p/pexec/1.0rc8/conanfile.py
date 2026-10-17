import os
import shutil

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

required_conan_version = ">=2.0"


class PexecConan(ConanFile):
    name = "pexec"
    version = "1.0rc8"
    description = "pexec - a tool for executing commands in parallel, locally or on remote hosts over SSH"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/pexec/"
    url = "https://ftp.gnu.org/gnu/pexec/pexec-1.0rc8.tar.gz"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # conanbuild env provides CONFIG_SHELL/SHELL (bash) so configure does
        # not run under the HMDFS-limited /bin/sh
        VirtualBuildEnv(self).generate()

    def _compilers(self):
        # R33: compilers from the toolchain conf, never from bare PATH
        exe = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = exe.get("c") or exe.get("cpp") or "clang"
        cxx = exe.get("cpp") or exe.get("c") or "clang++"
        return cc, cxx

    def build(self):
        apply_conandata_patches(self)
        # The 1990s-era config.status dies on HMDFS permission flakiness in
        # the deep conan cache folders (conf*/subs-1.sed: Permission denied);
        # run the in-source build from a shallow scratch copy instead.
        work = os.path.join(os.path.expanduser("~"), "tmp", "uc2",
                            "pexec-build-{}".format(self.version))
        if os.path.exists(work):
            shutil.rmtree(work)
        shutil.copytree(self.source_folder, work,
                        ignore=shutil.ignore_patterns(".git"))
        configure = os.path.join(work, "configure")
        # E011/E114: HMDFS rejects the umask 077 temp-dir dance in configure
        # (config.status then cannot re-read conf*/subs-*.sed)
        with open(configure, "r", errors="ignore") as f:
            script = f.read()
        if "(umask 077 && " in script:
            script = script.replace("(umask 077 && ", "(")
            with open(configure, "w") as f:
                f.write(script)
        # config.guess cannot recognise the HongMeng kernel; pin the triple
        cc, cxx = self._compilers()
        cmd = ('cd "{work}" && CC="{cc}" CXX="{cxx}" sh configure '
               '--build=aarch64-unknown-linux-gnu '
               '--prefix="{prefix}" && make -j1').format(
            work=work, cc=cc, cxx=cxx, prefix=self.package_folder)
        self.run(cmd)
        built = os.path.join(work, "src", "pexec")
        if not os.path.isfile(built):
            raise Exception("pexec binary not produced: " + built)
        shutil.copy2(built, os.path.join(self.build_folder, "pexec"))

    def package(self):
        from conan.tools.files import copy
        copy(self, "pexec", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        os.chmod(os.path.join(self.package_folder, "bin", "pexec"), 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
