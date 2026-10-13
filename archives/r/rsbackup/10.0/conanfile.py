"""Conan recipe for rsbackup 10.0 on native HarmonyOS PC."""

import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class RsbackupConan(ConanFile):
    name = "rsbackup"
    version = "10.0"
    description = "Backup and retention tool built on rsync"
    license = "GPL-3.0-or-later"
    homepage = "https://www.greenend.org.uk/rjk/rsbackup/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def requirements(self):
        self.requires("boost/1.90.0.4.4")
        self.requires("sqlite3/3.53.4")
        self.requires("rsync/3.3.0", run=True)

    def build_requirements(self):
        self.tool_requires("automake/1.19")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("This recipe targets native OHOS armv8")
        if cross_building(self):
            raise ConanInvalidConfiguration("Run the build and tests on HarmonyOS PC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _paths(self):
        paths = {name: Path(self.dependencies.host[name].package_folder)
                 for name in ("boost", "sqlite3", "rsync")}
        paths["automake"] = Path(self.dependencies.build["automake"].package_folder)
        return paths

    def _build_env(self, work):
        paths = self._paths()
        boost = paths["boost"]
        sqlite = paths["sqlite3"]
        rsync = paths["rsync"]
        automake = paths["automake"]
        for required in (boost / "lib/libboost_filesystem.so",
                         boost / "include/boost/uuid/uuid.hpp",
                         sqlite / "lib/libsqlite3.a", rsync / "bin/rsync"):
            if not required.is_file():
                raise ConanInvalidConfiguration(f"Published dependency is incomplete: {required}")
        env = Environment()
        env.prepend_path("PATH", str(automake / "bin"))
        env.prepend_path("PATH", str(rsync / "bin"))
        env.prepend_path("PATH", str(sqlite / "bin"))
        env.prepend_path("LD_LIBRARY_PATH", str(boost / "lib"))
        env.define("PERL5LIB", str(automake / "share/automake-1.19"))
        env.define("TMPDIR", str(work / "tmp"))
        env.define("PWD", str(work))
        env.define("RSBACKUP_TEST_ROOT", str(work / "tests"))
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        if compilers.get("cpp"):
            env.define("CXX", compilers["cpp"])
        env.define("CXXFLAGS", f"-I{boost / 'include'} -I{sqlite / 'include'} -Wno-error")
        env.define("LDFLAGS", f"-L{boost / 'lib'} -L{sqlite / 'lib'}")
        env.define("SQLITE3_CFLAGS", f"-I{sqlite / 'include'}")
        env.define("SQLITE3_LIBS", f"-L{sqlite / 'lib'} -lsqlite3")
        return env

    @staticmethod
    def _fix_config_status(work):
        status = work / "config.status"
        text = status.read_text()
        temp = str(work / "conan-config-status")
        text = text.replace('tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                            f"tmp={temp}")
        text = text.replace('tmp=./conf$$-$RANDOM', f"tmp={temp}")
        text = text.replace('test -d "$tmp"', 'mkdir -p "$tmp"')
        text = text.replace('(umask 077 && mkdir "$tmp")', 'true')
        status.write_text(text)

    @staticmethod
    def _adjust_config_expectations(work):
        # These four upstream fixtures describe defaults. The published OHOS
        # rsync lacks ACLs and HMDFS cannot read its security xattr, so the
        # configured defaults omit both while every other field stays checked.
        for name in ("empty.txt", "include.txt", "outdent.txt", "pruneparam.txt"):
            fixture = work / "tests" / "expect" / name
            text = fixture.read_text()
            old = "rsync-extra-options --xattrs --acls --open-noatime"
            if old not in text:
                raise ConanInvalidConfiguration(f"Upstream test fixture changed: {fixture}")
            fixture.write_text(text.replace(old, "rsync-extra-options --open-noatime"))

    def build(self):
        apply_conandata_patches(self)
        source = Path(self.source_folder)
        work = Path(self.build_folder)
        if source.resolve() != work.resolve():
            shutil.copytree(source, work, dirs_exist_ok=True)
        (work / "tmp").mkdir(exist_ok=True)
        self._adjust_config_expectations(work)
        env = self._build_env(work)
        with VirtualBuildEnv(self).vars().apply(), VirtualRunEnv(self).vars().apply(), env.vars(self).apply():
            self.run("autoreconf -si", cwd=str(work))
            self.run("./configure --no-create --disable-rsync-acls --disable-rsync-xattrs "
                     f"--prefix={self.package_folder} --build=aarch64-unknown-linux-ohos "
                     "--host=aarch64-unknown-linux-ohos", cwd=str(work))
            self._fix_config_status(work)
            self.run("bash config.status", cwd=str(work))
            self.run("make -j1", cwd=str(work))
            self.run("make -j1 check", cwd=str(work))

    def package(self):
        copy(self, "rsbackup", os.path.join(self.build_folder, "src"),
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
