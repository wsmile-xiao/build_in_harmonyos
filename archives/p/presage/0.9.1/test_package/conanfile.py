#!/usr/bin/env python3
"""Conan test_package for presage 0.9.1 — consumer-side smoke test (L1).

CI runs this automatically via `conan create` (which invokes test_package).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import load, save


class PresageTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Runtime configuration note: the autotools/conan convention bakes
        # --prefix=/ into the binaries, so /etc/presage.xml and /share/...
        # paths compiled into the preset profile do not exist on the
        # consumer side. Generate a profile that points at the real package
        # tree instead (@PKGDIR@), and redirect every writable state file
        # (ngram DB / dejavu memory / arpa tables) into this build folder
        # (@WRITEDIR@) so the consumer run never mutates the package folder.
        # 被测包的目录必须取 self.dependencies["presage"].package_folder ——
        # test_package 语境里 self.package_folder 是**测试包自身**的 package 目录
        # （cmake_layout 的 CMAKE_INSTALL_PREFIX 实证指向 test_package/），用它取
        # 数据文件会 FileNotFoundError（R4 实测：test_package/share/… 不存在）。
        tested = self.dependencies["presage"]
        pkg = tested.package_folder.replace("\\", "/")
        write_dir = self.build_folder.replace("\\", "/")
        tpl = load(self, os.path.join(self.source_folder, "presage-consumer.xml.in"))
        cfg = tpl.replace("@PKGDIR@", pkg).replace("@WRITEDIR@", write_dir)
        cfg_path = os.path.join(self.build_folder, "presage-consumer.xml")
        save(self, cfg_path, cfg)

        # Ship the trained ngram DB into the writable dir: an empty DB would
        # return no predictions and the count fingerprint assertion would
        # differ from the upstream-trained behaviour.
        db_src = os.path.join(tested.package_folder, "share", "presage", "database_en.db")
        db_dst = os.path.join(self.build_folder, "consumer_lm.db")
        shutil.copyfile(db_src, db_dst)

        # Isolate HOME so no profile/log file lands in the real user home
        # (sandbox-HOME discipline: upstream code may touch $HOME/.presage).
        home = os.path.join(self.build_folder, "home")
        os.makedirs(home, exist_ok=True)

        # §二.19 / PF3: run the real consumer binary directly (cmake.test()
        # would be judged a stub); the generated config is passed as argv[1].
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_presage")
        self.run(f'HOME="{home}" "{bin_path}" "{cfg_path}"', env="conanrun")
