#!/usr/bin/env python3
"""Conan recipe — libcommuni 3.7.0 (qmake build against qt5-qtbase).

Follows the CI-proven consumer pattern of libngf-qt/0.3.1: use the
qt5-qtbase package folder directly, fix its baked-in build paths
(qt.conf + mkspecs/**/*.pri) at build time, and drive libcommuni's
`sh configure` wrapper with qmake -spec linux-clang (E189/E447 class).
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibcommuniConan(ConanFile):
    name = "libcommuni"
    version = "3.7.0"
    description = "Cross-platform IRC framework written with Qt"
    license = "MIT"
    homepage = "https://communi.github.io"
    url = "https://github.com/communi/libcommuni"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # OHOS musl runtime cannot resolve versioned .so from user dirs
    # (LD_LIBRARY_PATH/DT_RPATH/RUNPATH all ineffective, see E589 draft)
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _fix_qtbase_paths(self, qtbase_pkg):
        """Point qt5-qtbase's qmake at its own package folder instead of the
        baked-in build directory (relocatability; libngf-qt proven pattern)."""
        qt_conf = os.path.join(qtbase_pkg, "bin", "qt.conf")
        with open(qt_conf, "w", encoding="utf-8") as f:
            f.write(
                "[EffectivePaths]\n"
                "Prefix=..\n"
                f"[DevicePaths]\n"
                f"Prefix={qtbase_pkg}\n"
                f"[Paths]\n"
                f"Prefix={qtbase_pkg}\n"
                f"HostPrefix={qtbase_pkg}\n"
                "Sysroot=\n"
                "SysrootifyPrefix=false\n"
                "TargetSpec=linux-clang\n"
                "HostSpec=linux-clang\n"
            )
        # mkspecs .pri files carry absolute paths of the qtbase build dir
        build_dir_pattern = re.compile(
            r"(/[^\s]*/\.conan2/p/b/qt5-q[0-9a-f]+/b)"
        )
        for modules_dir_name in ("modules", "modules-inst"):
            modules_dir = os.path.join(qtbase_pkg, "mkspecs", modules_dir_name)
            if not os.path.isdir(modules_dir):
                continue
            for pri_file in os.listdir(modules_dir):
                if not pri_file.endswith(".pri"):
                    continue
                pri_path = os.path.join(modules_dir, pri_file)
                with open(pri_path, "r", encoding="utf-8") as f:
                    content = f.read()
                fixed_content = build_dir_pattern.sub(qtbase_pkg, content)
                if fixed_content != content:
                    with open(pri_path, "w", encoding="utf-8") as f:
                        f.write(fixed_content)

    def build(self):
        apply_conandata_patches(self)
        qtbase = self.dependencies["qt5-qtbase"]
        self._fix_qtbase_paths(qtbase.package_folder)
        qmake = os.path.join(qtbase.package_folder, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException(
                "qt5-qtbase/5.15.2.2 does not provide the required bin/qmake tool"
            )
        inst = os.path.join(self.build_folder, "inst")
        args = [
            "--prefix", inst,
            "-nomake", "examples", "-nomake", "tests", "-no-icu",
            "--spec", "linux-clang",
        ]
        if not self.options.shared:
            args.append("-static")
        build_env = Environment()
        build_env.define("QTDIR", qtbase.package_folder)
        build_env.prepend_path("PATH", os.path.join(qtbase.package_folder, "bin"))
        build_env.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase.package_folder, "lib"))
        with build_env.vars(self).apply():
            # libcommuni's ./configure wraps qmake (resolves qmake via PATH)
            self.run(f'cd "{self.source_folder}" && sh configure {" ".join(args)}')
            jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)
            self.run(f'cd "{self.source_folder}" && make -j{jobs}')
            # qmake Makefiles stage via the configured --prefix (no DESTDIR)
            self.run(f'cd "{self.source_folder}" && make install')

    def package(self):
        # build() already staged via `make install` into the configured prefix
        inst = os.path.join(self.build_folder, "inst")
        for sub in ("lib", "include", "features"):
            src = os.path.join(inst, sub)
            if os.path.isdir(src):
                copy(self, "*", src, os.path.join(self.package_folder, sub))

    def package_info(self):
        self.cpp_info.libs = ["IrcCore", "IrcModel", "IrcUtil"]
        # propagate Qt linkage: static IrcCore references Qt5Core/Qt5Network
        # symbols that consumers must resolve
        self.cpp_info.requires = ["qt5-qtbase::Qt5Core", "qt5-qtbase::Qt5Network"]
