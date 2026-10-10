"""QDirStat 2.0, built with its upstream Qt 6 qmake project."""

import hashlib
import os
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get, unzip
from conan.tools.layout import basic_layout


class QDirStatConan(ConanFile):
    name = "qdirstat"
    version = "2.0"
    description = "Graphical disk usage analyzer for Qt 6"
    license = "GPL-2.0-only"
    homepage = "https://github.com/shundhammer/qdirstat"
    url = "https://github.com/shundhammer/qdirstat"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # Qt5Compat 6.11.1 requires this exact Qt base version.
        self.requires("qtbase/6.11.1")
        self.requires("qt5compat/6.11.1")
        self.requires("zlib/1.3.2")
        self.requires("gettext/0.22.5.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"][str(self.version)]
        local_archive = os.environ.get("QDIRSTAT_SOURCE_ARCHIVE")
        if local_archive:
            with open(local_archive, "rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual.lower() != source["sha256"].lower():
                raise ConanException("QDirStat source archive SHA-256 mismatch")
            unzip(self, local_archive, destination=self.source_folder, strip_root=True)
        else:
            get(self, **source, strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        qt = self.dependencies["qtbase"].package_folder
        compat = self.dependencies["qt5compat"].package_folder
        zlib = self.dependencies["zlib"].package_folder
        gettext = self.dependencies["gettext"].package_folder
        qmake = os.path.join(qt, "bin", "qmake6")
        if not os.path.isfile(qmake):
            raise ConanException("The published qtbase package has no qmake6")

        compiler = self.conf.get("tools.build:compiler_executables", default={})
        cxx = compiler.get("cpp")
        cc = compiler.get("c")
        if not cxx or not cc:
            raise ConanException("The OHOS profile must specify its C and C++ compilers")

        env = Environment()
        # Qt's published Core5Compat qmake metadata uses QT_MODULE_LIB_BASE,
        # which points at qtbase instead of this separately packaged module.
        # Shadow only these two module descriptors inside the build folder.
        overlay = os.path.join(self.build_folder, "qmake-overlay")
        modules = os.path.join(overlay, "mkspecs", "modules")
        os.makedirs(modules, exist_ok=True)
        for name in ("qt_lib_core5compat.pri", "qt_lib_core5compat_private.pri"):
            original = os.path.join(compat, "mkspecs", "modules", name)
            with open(original, encoding="utf-8") as stream:
                contents = stream.read()
            contents = contents.replace("$$QT_MODULE_LIB_BASE", os.path.join(compat, "lib"))
            contents = contents.replace("$$QT_MODULE_INCLUDE_BASE", os.path.join(compat, "include"))
            with open(os.path.join(modules, name), "w", encoding="utf-8") as stream:
                stream.write(contents)

        env = Environment()
        env.define("QMAKEPATH", overlay)
        env.prepend_path("LIBRARY_PATH", os.path.join(zlib, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qt, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(compat, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(gettext, "lib"))
        with env.vars(self).apply():
            self.run(
                '"{}" "{}" QMAKE_CC="{}" QMAKE_CXX="{}" '
                'QMAKE_LINK="{}" "INCLUDEPATH+={}" "INCLUDEPATH+={}" '
                '"INCLUDEPATH+={}" "LIBS+=-L{}" "LIBS+=-L{}" '
                '"LIBS+=-L{}" "LIBS+=-lintl"'.format(
                    qmake,
                    os.path.join(self.source_folder, "src", "src.pro"),
                    cc, cxx, cxx,
                    os.path.join(compat, "include"),
                    os.path.join(compat, "include", "QtCore5Compat"),
                    os.path.join(gettext, "include"),
                    os.path.join(compat, "lib"),
                    os.path.join(zlib, "lib"),
                    os.path.join(gettext, "lib"),
                ),
                cwd=self.build_folder,
            )
            with open(os.path.join(self.build_folder, "Makefile"), encoding="utf-8") as stream:
                makefile = stream.read()
            expected = os.path.join(compat, "lib", "libQt6Core5Compat.so")
            if expected not in makefile:
                raise ConanException("qmake did not link the published Qt5Compat library")
            self.run("make -j1", cwd=self.build_folder)
        # Upstream's test/ directory has data fixtures but no qmake test target.
        self.output.info("QDIRSTAT_UPSTREAM_TESTS_NONE")

    def package(self):
        copy(self, "qdirstat", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        executable = os.path.join(self.package_folder, "bin", "qdirstat")
        if not os.path.isfile(executable):
            raise ConanException("qmake did not produce the qdirstat executable")
        copy(self, "qdirstat-cache-writer", src=os.path.join(self.source_folder, "scripts"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "*.desktop", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "share", "applications"), keep_path=False)
        copy(self, "qdirstat.svg", src=os.path.join(self.source_folder, "src", "icons"),
             dst=os.path.join(self.package_folder, "share", "icons", "hicolor", "scalable", "apps"),
             keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        if str(self.settings.os) == "OHOS":
            self._sign_executable(executable)

    @staticmethod
    def _sign_executable(executable):
        signer = shutil.which("binary-sign-tool")
        if not signer:
            raise ConanException("binary-sign-tool is required to sign the installed OHOS ELF")
        original_mode = stat.S_IMODE(os.stat(executable).st_mode)
        with tempfile.TemporaryDirectory(prefix=".qdirstat-sign-", dir=os.path.dirname(executable)) as temp:
            signed = os.path.join(temp, "signed")
            result = subprocess.run(
                [signer, "sign", "-inFile", executable, "-outFile", signed, "-selfSign", "1"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode or not os.path.isfile(signed):
                raise ConanException("Signing qdirstat failed: " + (result.stderr or result.stdout))
            with open(signed, "rb") as stream:
                if stream.read(4) != b"\x7fELF":
                    raise ConanException("Signing qdirstat produced a non-ELF file")
            os.replace(signed, executable)
            os.chmod(executable, original_mode | 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
