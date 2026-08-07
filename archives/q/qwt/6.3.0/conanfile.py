#!/usr/bin/env python3
"""Conan recipe for qwt 6.3.0 — qmake-based Qt plotting library (OHOS).

qwt is built with qmake from the qtbase dependency (Qt 6.11.1, OHOS aarch64).
OHOS adaptations (vs upstream):
  - QwtSvg / QwtOpenGL / QwtDesigner / QwtExamples / QwtPlayground disabled
    (qtbase for OHOS ships no QtSvg/QtOpenGL/QtDesigner modules)
  - QtPrintSupport absent in OHOS qtbase -> QT_NO_PRINTER guard added in
    src.pri / tests.pri and qwt_plot_renderer.cpp / qwt_polar_renderer.cpp
  - src.pri: explicit "QT += widgets" (QwtWidgets branch)
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import Environment
from conan.tools.gnu import AutotoolsToolchain
import os
import shutil
import tarfile


class QwtConan(ConanFile):
    name = "qwt"
    version = "6.3.0"
    description = "Qt Widgets for Technical Applications (qwt) — plotting widgets for Qt"
    license = "LGPL-2.1"
    homepage = "https://qwt.sourceforge.io/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        # 本地已有 tarball 时优先使用（本地 CI 加速），否则走官方 URL
        local_tar = os.path.join(os.path.expanduser("~/builds"), "qwt-6.3.0.tar.bz2")
        if os.path.exists(local_tar):
            tmp = os.path.join(self.source_folder, "_tmp")
            os.makedirs(tmp, exist_ok=True)
            shutil.copy(local_tar, os.path.join(tmp, "qwt-6.3.0.tar.bz2"))
            with tarfile.open(os.path.join(tmp, "qwt-6.3.0.tar.bz2"), "r:bz2") as tf:
                tf.extractall(tmp, filter="data")
            src_dir = os.path.join(tmp, "qwt-6.3.0")
            for item in os.listdir(src_dir):
                shutil.move(os.path.join(src_dir, item),
                            os.path.join(self.source_folder, item))
            shutil.rmtree(tmp)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Locate qmake from the qtbase dependency and expose it + Qt include/lib paths
        qt = self.dependencies["qtbase"]
        qt_root = qt.package_folder
        env = Environment()
        env.define_path("QMAKE_BIN", qt_root + "/bin/qmake")
        env.append_path("PATH", qt_root + "/bin")
        env.append_path("LD_LIBRARY_PATH", qt_root + "/lib")
        env.vars(self).save_script("conanbuild_qwt")
        tc = AutotoolsToolchain(self)  # keep toolchain for cross compiler env
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        qt = self.dependencies["qtbase"]
        qt_root = qt.package_folder
        self.run(f'{qt_root}/bin/qmake -spec harmonyos-clang '
                 f'"QMAKE_LFLAGS+=-ccc-gcc-name g++" qwt.pro', cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # qmake INSTALLS with DESTDIR-style staging into package folder
        self.run("make install INSTALL_ROOT=%s" % self.package_folder,
                 cwd=self.source_folder)
        # OHOS musl 加载器对 qmake strip 后的库符号解析失败(symbol not found)，
        # 用未 strip 的构建产物覆盖，保证消费者可正常加载
        dst_lib = os.path.join(self.package_folder, "usr/local/qwt-6.3.0/lib")
        copy(self, "libqwt.so*", src=os.path.join(self.source_folder, "lib"), dst=dst_lib)
        # 重建符号链接（copy() 不保留 symlink）
        for link in ("libqwt.so", "libqwt.so.6", "libqwt.so.6.3"):
            lp = os.path.join(dst_lib, link)
            if os.path.islink(lp) or os.path.exists(lp):
                os.remove(lp)
            os.symlink("libqwt.so.6.3.0", lp)

    def package_info(self):
        self.cpp_info.libs = ["qwt"]
        self.cpp_info.includedirs = ["usr/local/qwt-6.3.0/include"]
        self.cpp_info.libdirs = ["usr/local/qwt-6.3.0/lib"]
