"""libQGLViewer Qt5 core library for HarmonyOS PC."""

import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import get
from conan.tools.layout import basic_layout


class LibqglviewerConan(ConanFile):
    name = "libqglviewer"
    version = "2.9.1"
    package_type = "shared-library"
    description = "Qt OpenGL viewer library"
    homepage = "https://libqglviewer.com/"
    license = "GPL-2.0-only OR GPL-3.0-only"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "cmake-harmony/*"

    def requirements(self):
        # Public QGLViewer headers include QtCore/QtWidgets headers, so
        # downstream consumers need Qt's include dirs as well as its libs.
        self.requires("qt5-qtbase/5.15.2.2",
                      transitive_headers=True, transitive_libs=True)
        # Public config.h includes GL/glu.h, whose declarations require GL.
        self.requires("glu/9.0.3",
                      transitive_headers=True, transitive_libs=True)
        self.requires("mesa/24.3.4.1",
                      transitive_headers=True, transitive_libs=True)
        # Qt5 and GLU/Mesa publish compatible 2.8.x expat binaries but use
        # distinct patch revisions in their recipes.
        self.requires("expat/2.8.2.1.1", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("LIBQGLVIEWER_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("local source archive is not a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        qt = self.dependencies["qt5-qtbase"].package_folder
        glu = self.dependencies["glu"].package_folder
        mesa = self.dependencies["mesa"].package_folder
        tc = CMakeToolchain(self)
        tc.variables["QGLVIEWER_UPSTREAM"] = self.source_folder
        tc.variables["QT5_PREFIX"] = qt
        tc.variables["GLU_INCLUDE_DIR"] = os.path.join(glu, "include")
        tc.variables["MESA_INCLUDE_DIR"] = os.path.join(mesa, "include")
        tc.variables["GLU_LIBRARY"] = os.path.join(glu, "lib", "libGLU.so")
        tc.variables["MESA_LIBRARY"] = os.path.join(mesa, "lib", "libOSMesa.so")
        tc.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    @staticmethod
    def _sign_elf(path):
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not signer or not readelf:
            raise ConanInvalidConfiguration("OHOS signer/readelf missing")
        original = Path(path)
        pending = original.with_name(original.name + ".qgl-signing")
        signed = original.with_name(original.name + ".qgl-signed")
        if pending.exists() or signed.exists():
            raise ConanInvalidConfiguration("stale signing sibling")
        try:
            shutil.copy2(original, pending)
            subprocess.run([signer, "sign", "-inFile", str(pending),
                            "-outFile", str(signed), "-selfSign", "1"],
                           check=True, capture_output=True, text=True, timeout=40)
            result = subprocess.run([readelf, "-S", str(signed)], check=True,
                                    capture_output=True, text=True, timeout=20)
            if ".codesign" not in result.stdout:
                raise ConanException("signed ELF lacks .codesign")
            os.chmod(signed, original.stat().st_mode)
            os.replace(signed, original)
        finally:
            for temporary in (pending, signed):
                if temporary.exists():
                    temporary.unlink()

    def build(self):
        cmake = CMake(self)
        qt = self.dependencies["qt5-qtbase"].package_folder
        environment = Environment()
        environment.prepend_path("LD_LIBRARY_PATH", os.path.join(qt, "lib"))
        with environment.vars(self).apply():
            cmake.configure(build_script_folder=os.path.join(
                self.export_sources_folder, "cmake-harmony"))
            cmake.build(build_tool_args=["-j1"])
        self.output.info("UPSTREAM_0_OF_0_NO_REGISTERED_SUITE")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Qt5's package has QtOpenGL but omits its CMakeDeps component. This
        # forwarding header preserves upstream's public #include <QGL> API.
        Path(self.package_folder, "include", "QGL").write_text(
            "#include <QtOpenGL/QGL>\n", encoding="utf-8")
        if str(self.settings.os) == "OHOS":
            real = [p for p in Path(self.package_folder, "lib").glob("libQGLViewer-qt5.so*")
                    if p.is_file() and not p.is_symlink()]
            if len(real) != 1:
                raise ConanException("expected exactly one real QGLViewer ELF")
            self._sign_elf(real[0])
        license_file = Path(self.source_folder, "LICENCE")
        if license_file.is_file():
            licenses = Path(self.package_folder, "licenses")
            licenses.mkdir(exist_ok=True)
            shutil.copy2(license_file, licenses / "LICENCE")
            exception = Path(self.source_folder, "GPL_EXCEPTION")
            if exception.is_file():
                shutil.copy2(exception, licenses / "GPL_EXCEPTION")

    def package_info(self):
        self.cpp_info.libs = ["QGLViewer-qt5"]
        self.cpp_info.requires = [
            "qt5-qtbase::Qt5Core", "qt5-qtbase::Qt5Gui",
            "qt5-qtbase::Qt5Widgets", "qt5-qtbase::Qt5Xml", "glu::glu",
            "mesa::mesa",
        ]
        self.cpp_info.system_libs = ["Qt5OpenGL"]
        self.cpp_info.defines = ["NO_VECTORIAL_RENDER"]
        self.runenv_info.prepend_path("LD_LIBRARY_PATH",
                                      os.path.join(self.package_folder, "lib"))
