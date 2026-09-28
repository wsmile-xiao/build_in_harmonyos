#!/usr/bin/env python3
"""Conan recipe for kylin-scanner 1.0.0.

kylin-scanner is the openKylin Qt5 GUI scanner application
(gitee.com/openkylin/kylin-scanner). Upstream uses qmake (Qt5) with
pkg-config deps (gio-2.0, opencv4), leptonica/tesseract and a hardcoded
x86_64 sane path. This recipe builds it with qt5-qtbase's qmake and
injects all dependency include/lib paths from Conan packages via qmake
command-line variable assignments (no .pc files needed).

Build system: qmake (upstream, kept)
License: GPL-3.0-or-later
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class KylinScannerConan(ConanFile):
    name = "kylin-scanner"
    version = "1.0.0"
    description = "openKylin Qt5 scanner application with image post-processing and OCR"
    license = "GPL-3.0-or-later"
    homepage = "https://gitee.com/openkylin/kylin-scanner"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Qt5 base (QtCore/QtGui/Qt5Widgets + qmake/moc/uic/rcc tools)
        self.requires("qt5-qtbase/5.15.2.2")
        # pkg-config deps of upstream src.pro
        self.requires("glib/2.84.0.2")        # gio-2.0 / gio-unix-2.0
        self.requires("opencv/4.12.0")        # opencv4
        # LIBS -llept / -ltesseract / -lsane
        self.requires("leptonica/1.87.0")
        self.requires("tesseract/5.5.3")
        self.requires("sane-backends/1.2.1")
        # libsane 链接了 libxml2（sane-backends 的传递依赖），
        # 需加入 RUNPATH 以避免运行时符号找不到
        self.requires("libxml2/2.15.3")
        # 对齐 qt5-qtbase(zlib/1.3.1) 与 glib(zlib/1.3.1.1) 的版本冲突
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("expat/2.8.2.1", override=True)
        self.requires("openssl/3.5.6.1", override=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(self, url=url, sha256=source_data["sha256"], strip_root=True)
                return
            except Exception as error:
                self.output.warning(f"Failed to download source from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download source from all mirrors")

    def _fix_qtbase_paths(self, qtbase_pkg):
        """Make qt5-qtbase's qt.conf / .pri files relocatable (see libngf-qt)."""
        import re
        qt_conf = os.path.join(qtbase_pkg, "bin", "qt.conf")
        if os.path.isfile(qt_conf):
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
        build_dir_pattern = re.compile(r"(/[^\s]*/\.conan2/p/b/qt5-q[0-9a-f]+/b)")
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
                fixed = build_dir_pattern.sub(qtbase_pkg, content)
                if fixed != content:
                    with open(pri_path, "w", encoding="utf-8") as f:
                        f.write(fixed)

    def _all_lib_dirs(self):
        """收集全部（含传递）依赖的 lib 目录，用于注入 RUNPATH。"""
        seen = set()
        dirs = []
        stack = list(self.dependencies.values())
        while stack:
            dep = stack.pop()
            if not dep.package_folder:
                continue
            for d in (dep.cpp_info.libdirs or []):
                if not d:
                    continue
                p = d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
                if os.path.isdir(p) and p not in seen:
                    seen.add(p); dirs.append(p)
            stack.extend(dep.dependencies.values())
        return dirs

    def _dep_qmake_args(self):
        """Build qmake command-line INCLUDEPATH/LIBS additions from Conan deps."""
        include_dirs = []
        for dep_name in ("qt5-qtbase", "glib", "opencv", "leptonica", "tesseract", "sane-backends", "libxml2"):
            dep = self.dependencies[dep_name]
            info = dep.cpp_info
            for inc in (info.includedirs or []):
                include_dirs.append(inc if os.path.isabs(inc) else os.path.join(dep.package_folder, inc))
            # glib style layouts: headers also under include/glib-2.0, lib/glib-2.0/include
            for extra in ("include/glib-2.0", "lib/glib-2.0/include", "include/gio-unix-2.0"):
                cand = os.path.join(dep.package_folder, extra)
                if os.path.isdir(cand) and cand not in include_dirs:
                    include_dirs.append(cand)
        lib_dirs = self._all_lib_dirs()
        args = []
        for inc in include_dirs:
            args.append(f"INCLUDEPATH+={shlex.quote(inc)}")
        for libd in lib_dirs:
            args.append(f"LIBS+=-L{shlex.quote(libd)} -Wl,-rpath,{shlex.quote(libd)}")
        libs = [
            "-lgio-2.0", "-lgobject-2.0", "-lglib-2.0",
            "-lopencv_core", "-lopencv_imgproc", "-lopencv_imgcodecs",
            "-lopencv_highgui", "-lopencv_photo",
            "-lleptonica", "-ltesseract", "-lsane",
        ]
        args.append("LIBS+=" + " ".join(libs))
        return args

    def build(self):
        apply_conandata_patches(self)
        qtbase = self.dependencies["qt5-qtbase"]
        self._fix_qtbase_paths(qtbase.package_folder)
        qmake = os.path.join(qtbase.package_folder, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanInvalidConfiguration(
                "qt5-qtbase/5.15.2.2 does not provide the required bin/qmake tool"
            )
        build_env = Environment()
        build_env.define("QTDIR", qtbase.package_folder)
        build_env.prepend_path("PATH", os.path.join(qtbase.package_folder, "bin"))
        qmake_args = " ".join(f'"{a}"' if not a.startswith(("INCLUDEPATH+=")) else a
                              for a in self._dep_qmake_args())
        pro = os.path.join(self.source_folder, "kylin-scanner.pro")
        with build_env.vars(self).apply():
            self.run(f'cd "{self.source_folder}" && {shlex.quote(qmake)} -spec linux-clang '
                     f'"{pro}" {qmake_args}')
            jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)
            self.run(f'cd "{self.source_folder}" && make -j{jobs}')

    def package(self):
        src = self.source_folder
        # executable
        for cand in (os.path.join(src, "src", "kylin-scanner"),):
            if os.path.isfile(cand):
                copy(self, "kylin-scanner", src=os.path.join(src, "src"),
                     dst=os.path.join(self.package_folder, "bin"), keep_path=False)
                os.chmod(os.path.join(self.package_folder, "bin", "kylin-scanner"), 0o755)
                break
        else:
            raise ConanInvalidConfiguration("kylin-scanner binary was not built")
        # resources
        copy(self, "*.qm", src=os.path.join(src, "src", "translations"),
             dst=os.path.join(self.package_folder, "res", "kylin-scanner", "translations"),
             keep_path=False)
        copy(self, "*.png", src=os.path.join(src, "src", "data"),
             dst=os.path.join(self.package_folder, "res", "kylin-scanner", "icons"),
             keep_path=False)
        copy(self, "*.desktop", src=os.path.join(src, "src", "data"),
             dst=os.path.join(self.package_folder, "res", "kylin-scanner", "applications"),
             keep_path=False)
        copy(self, "COPYING", src=src,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        # OHOS 平台：签名可执行文件
        if self.settings.os == "OHOS":
            self._sign_binaries()

    def _sign_binaries(self):
        """OHOS 平台对可执行文件进行代码签名（ML-0043）"""
        import glob
        bindir = os.path.join(self.package_folder, "bin")
        bins = glob.glob(os.path.join(bindir, "*"))
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for b in bins:
            if not os.path.isfile(b):
                continue
            self.run(f'{objcopy} --remove-section .codesign "{b}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{b}" -outFile "{b}" -selfSign 1')

    def package_id(self):
        del self.info.settings.compiler

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
