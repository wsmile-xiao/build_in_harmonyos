#!/usr/bin/env python3
"""Conan recipe for QScintilla 2.14.1 on OpenHarmony PC."""
import glob
import os
import shlex
import subprocess

from conan.tools.build import build_jobs, can_run

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, replace_in_file


class QScintilla2Conan(ConanFile):
    name = "qscintilla2"
    version = "2.14.1"
    description = "QScintilla editing component for Qt, packaged for OpenHarmony PC"
    license = "GPL-3.0-only OR LicenseRef-Riverbank-Commercial"
    homepage = "https://www.riverbankcomputing.com/software/qscintilla/"
    url = "https://www.riverbankcomputing.com/software/qscintilla/download"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._patch_printsupport()

    def requirements(self):
        self.requires("qtbase/6.11.1")

    def generate(self):
        qt_root = self.dependencies["qtbase"].package_folder
        env = Environment()
        env.define_path("QMAKE_BIN", self._qmake())
        env.append_path("PATH", os.path.join(qt_root, "bin"))
        env.append_path("LD_LIBRARY_PATH", os.path.join(qt_root, "lib"))
        env.vars(self).save_script("conanbuild_qscintilla")

    def build(self):
        config = str(self.settings.build_type).lower()
        if config not in ("debug", "release"):
            config = "release"
        if not self.options.shared:
            config += " staticlib"
        qmake = self._qmake()
        pro_file = os.path.join(self.source_folder, "src", "qscintilla.pro")
        self.run("{} {} CONFIG+={}".format(
            shlex.quote(qmake), shlex.quote(pro_file), shlex.quote(config)))
        self.run("make -j{}".format(build_jobs(self)))

    def package(self):
        self.run("make install INSTALL_ROOT={}".format(shlex.quote(self.package_folder)))
        self._normalize_install_tree()
        self._drop_printer_header_if_unavailable()
        if str(self.settings.os) == "OHOS" and self.options.shared:
            self._sign_shared_libs()
        self._build_upstream_example()
        self._run_python_config_probe()

    def _patch_printsupport(self):
        pro = os.path.join(self.source_folder, "src", "qscintilla.pro")
        printer_header = os.path.join(self.source_folder, "src", "Qsci", "qsciprinter.h")
        for path, old, new in (
            (pro, "!ios:QT += printsupport",
             "qtHaveModule(printsupport) { QT += printsupport } else { DEFINES += QT_NO_PRINTER }"),
            (pro, "!ios:HEADERS += ./Qsci/qsciprinter.h",
             "!ios:qtHaveModule(printsupport):HEADERS += ./Qsci/qsciprinter.h"),
            (pro, "!ios:SOURCES += qsciprinter.cpp",
             "!ios:qtHaveModule(printsupport):SOURCES += qsciprinter.cpp"),
            (os.path.join(self.source_folder, "src", "features", "qscintilla2.prf"),
             "!ios:QT += printsupport",
             "qtHaveModule(printsupport) { QT += printsupport } else { DEFINES += QT_NO_PRINTER }"),
            (os.path.join(self.source_folder, "src", "features_staticlib", "qscintilla2.prf"),
             "!ios:QT += printsupport",
             "qtHaveModule(printsupport) { QT += printsupport } else { DEFINES += QT_NO_PRINTER }"),
            (printer_header,
             "#include <qprinter.h>\n\n#if !defined(QT_NO_PRINTER)",
             "#if !defined(QT_NO_PRINTER)\n#include <qprinter.h>"),
        ):
            replace_in_file(self, path, old, new)

    def _drop_printer_header_if_unavailable(self):
        if self._qt_has_printsupport():
            return
        installed = os.path.join(self.package_folder, "include", "Qsci", "qsciprinter.h")
        if os.path.isfile(installed):
            os.remove(installed)

    def _qt_has_printsupport(self):
        qt_prefix = self.dependencies["qtbase"].package_folder
        return os.path.isdir(os.path.join(qt_prefix, "lib", "cmake", "Qt6PrintSupport"))

    def _build_upstream_example(self):
        example_dir = os.path.join(self.source_folder, "example")
        pro_file = os.path.join(example_dir, "application.pro")
        if not os.path.isfile(pro_file):
            raise ConanException("QScintilla upstream example project was not found")
        qmake = self._qmake()
        build_dir = os.path.join(self.build_folder, "upstream-example")
        os.makedirs(build_dir, exist_ok=True)
        self.run("QMAKEFEATURES={} {} {} CONFIG+=release INCLUDEPATH+={} LIBS+=-L{}".format(
            shlex.quote(os.path.join(self.package_folder, "mkspecs", "features")),
            shlex.quote(qmake),
            shlex.quote(pro_file),
            shlex.quote(os.path.join(self.package_folder, "include")),
            shlex.quote(os.path.join(self.package_folder, "lib"))), cwd=build_dir)
        self.run("make -j{}".format(build_jobs(self)), cwd=build_dir)
        executable = os.path.join(build_dir, "application")
        if os.path.isfile(executable) and can_run(self):
            library_path = os.pathsep.join([
                os.path.join(self.package_folder, "lib"),
                self._qt_lib_dir(),
            ])
            self.run(
                "QT_QPA_PLATFORM=offscreen LD_LIBRARY_PATH={} timeout 5s {} || test $? -eq 124".format(
                    shlex.quote(library_path), shlex.quote(executable)))

    def _run_python_config_probe(self):
        source = os.path.join(self.source_folder, "Python", "config-tests", "cfgtest_Qsci.cpp")
        if not os.path.isfile(source):
            raise ConanException("QScintilla upstream cfgtest_Qsci.cpp was not found")
        qmake = self._qmake()
        build_dir = os.path.join(self.build_folder, "upstream-cfgtest")
        os.makedirs(build_dir, exist_ok=True)
        project = os.path.join(build_dir, "cfgtest_Qsci.pro")
        with open(project, "w", encoding="utf-8") as handle:
            handle.write("QT += core\n")
            handle.write("CONFIG += console c++11\n")
            handle.write("CONFIG -= app_bundle\n")
            handle.write("SOURCES += {}\n".format(source.replace("\\", "/")))
            handle.write("INCLUDEPATH += {}\n".format(os.path.join(self.package_folder, "include").replace("\\", "/")))
            handle.write("LIBS += -L{} -lqscintilla2_qt6\n".format(os.path.join(self.package_folder, "lib").replace("\\", "/")))
        self.run("{} {}".format(shlex.quote(qmake), shlex.quote(project)), cwd=build_dir)
        self.run("make -j{}".format(build_jobs(self)), cwd=build_dir)
        executable = os.path.join(build_dir, "cfgtest_Qsci")
        output = os.path.join(build_dir, "qscintilla-version.txt")
        if not can_run(self):
            self.output.info("codex: QScintilla cfgtest execution skipped because target execution is not available")
            return
        library_path = os.pathsep.join([
            os.path.join(self.package_folder, "lib"),
            self._qt_lib_dir(),
        ])
        self.run("LD_LIBRARY_PATH={} {} {}".format(
            shlex.quote(library_path), shlex.quote(executable), shlex.quote(output)))
        with open(output, "r", encoding="utf-8") as handle:
            content = handle.read()
        if "2.14.1" not in content:
            raise ConanException("Unexpected QScintilla cfgtest output: {}".format(content.strip()))

    def _normalize_install_tree(self):
        prefix = self._qt_prefix()
        if not prefix:
            raise ConanInvalidConfiguration("Qt installation prefix disappeared during package()")
        staged_prefix = os.path.join(self.package_folder, prefix.lstrip(os.sep))
        if not os.path.isdir(staged_prefix):
            dirnames = ("include", "lib", "mkspecs", "share", "translations")
            staged_dirs = []
            for root, dirs, _files in os.walk(self.package_folder):
                depth = root[len(self.package_folder):].count(os.sep)
                if depth > 6:
                    dirs[:] = []
                    continue
                for dirname in dirnames:
                    candidate = os.path.join(root, dirname)
                    if os.path.isdir(candidate):
                        staged_dirs.append(candidate)
            for src in staged_dirs:
                dst = os.path.join(self.package_folder, os.path.basename(src))
                if os.path.abspath(src) == os.path.abspath(dst):
                    continue
                if os.path.exists(dst):
                    self.run("cp -a {}/. {}".format(shlex.quote(src), shlex.quote(dst)))
                else:
                    self.run("mv {} {}".format(shlex.quote(src), shlex.quote(dst)))
            return
        for dirname in ("include", "lib", "mkspecs", "share", "translations"):
            src = os.path.join(staged_prefix, dirname)
            dst = os.path.join(self.package_folder, dirname)
            if os.path.exists(src):
                if os.path.exists(dst):
                    self.run("cp -a {}/. {}".format(shlex.quote(src), shlex.quote(dst)))
                else:
                    self.run("mv {} {}".format(shlex.quote(src), shlex.quote(dst)))

    def _qt_prefix(self):
        qmake = self._qmake()
        if not qmake:
            return None
        try:
            result = subprocess.run(
                [qmake, "-query", "QT_INSTALL_PREFIX"],
                capture_output=True,
                text=True,
                timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        return os.path.dirname(os.path.dirname(qmake))

    def _qt_lib_dir(self):
        return os.path.join(self.dependencies["qtbase"].package_folder, "lib")

    def _qmake(self):
        return self._qmake_in(self.dependencies["qtbase"].package_folder)

    def _qmake_in(self, prefix):
        for relpath in (
            os.path.join("bin", "qmake"),
            os.path.join("bin", "qmake6"),
            os.path.join("libexec", "qmake"),
            os.path.join("libexec", "qmake6"),
        ):
            candidate = os.path.join(prefix, relpath)
            if os.path.isfile(candidate):
                return candidate
        return None

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        shared_objects = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        shared_objects += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not shared_objects:
            return
        objcopy = os.environ.get("HNP_LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("HNP_BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException("Required OHOS signing tool not found: {}".format(tool))
        for shared_object in shared_objects:
            if os.path.islink(shared_object):
                continue
            self._remove_codesign_section(objcopy, shared_object)
            self.run("{} sign -inFile {} -outFile {} -selfSign 1".format(
                shlex.quote(signer),
                shlex.quote(shared_object),
                shlex.quote(shared_object)))

    def _remove_codesign_section(self, objcopy, shared_object):
        try:
            probe = subprocess.run(
                [objcopy, "--dump-section", ".codesign=/dev/null", shared_object],
                text=True,
                capture_output=True,
                check=False)
        except OSError as exc:
            raise ConanException("Required OHOS objcopy tool failed: {}".format(objcopy)) from exc
        if probe.returncode != 0:
            return
        self.run("{} --remove-section .codesign {}".format(
            shlex.quote(objcopy),
            shlex.quote(shared_object)))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "qscintilla2")
        self.cpp_info.set_property("cmake_target_name", "qscintilla2::qscintilla2")
        self.cpp_info.libs = ["qscintilla2_qt6"]
        self.cpp_info.includedirs = ["include"]
