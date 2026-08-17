#!/usr/bin/env python3
"""Conan recipe — wiliki 0.6.2 (Wiki engine written in Gauche Scheme).

wiliki is a Wiki engine written in Gauche Scheme.  It is a pure-Scheme
package: configure generates the Makefiles (and WiLiKi.gpd via
gauche-package), make runs gosh to produce wiliki/version.scm, and install
copies the .scm modules into Gauche's site lib plus a ja locale.

Key OHOS adaptations:
  - HMDFS config.status temporary-directory creation fails with umask 077
    (E011); the generated configure is patched to use umask 022.

File location: archives/w/wiliki/0.6.2/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class WilikiConan(ConanFile):
    name = "wiliki"
    version = "0.6.2"
    description = "WiLiKi is a Wiki engine written in Gauche Scheme"
    license = "BSD-3-Clause"
    homepage = "https://practical-scheme.net/wiliki/"
    url = "https://github.com/shirok/WiLiKi"

    # wiliki installs only Scheme modules (.scm/.gpd/.mo), no executables and
    # no C library, so it is classified as a library (R38: no commands.json).
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # Conan requires library package_type to declare a shared option; wiliki
    # is pure Scheme so the value has no build effect (kept static by default).
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        # wiliki is a Gauche application: configure needs gosh/gauche-config
        # on PATH, and the installed modules are loaded by gosh at runtime.
        # gauche/0.9.15.2 is published to the artifact repo (R36 passed at W0).
        self.requires("gauche/0.9.15.2")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # wiliki's Makefile uses in-source relative paths (./gen-version,
        # > wiliki/version.scm), so it must be built in-source: the build
        # folder is the source folder itself (no out-of-source VPATH).
        basic_layout(self)
        self.folders.build = self.folders.source

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # wiliki is pure Scheme: no shared/static C library to build.  Install
        # under / so that make install DESTDIR=<package_folder> lands the
        # modules directly in <package>/share/gauche-0.98/site/lib/... .
        tc.configure_args.append("--prefix=/")
        # Provide the gauche toolchain (gosh, gauche-config, gauche-package,
        # gauche-install, gauche-cesconv) plus its module search paths
        # (GAUCHE_LOAD_PATH / GAUCHE_DYNLOAD_PATH) to configure/make.
        env = tc.environment()
        if self.dependencies.get("gauche"):
            g = self.dependencies["gauche"]
            gauche_bin = os.path.join(g.package_folder, "bin")
            gauche_lib = os.path.join(g.package_folder, "lib")
            gosh_path = os.path.join(gauche_bin, "gosh")
            # Prepend gauche's own bin so its tools (and their shebangs) win
            # over any system deployment on PATH.
            env.prepend_path("PATH", gauche_bin)
            # gosh loads libgauche at runtime; the packaged gosh has no
            # baked-in RPATH, so consumers must provide LD_LIBRARY_PATH.
            env.prepend_path("LD_LIBRARY_PATH", gauche_lib)
            env.compose_env(g.runenv_info)
            # Portability: the published gauche/0.9.15.2 tool scripts carry a
            # shebang pointing at the publisher's conan cache
            # (/storage/.../.conan2/...), which does not exist in the CI
            # sandbox (/storage/.../.cache/conan2/...).  Provide sh wrappers
            # that invoke the real scripts through gosh so configure/make can
            # run on any machine (same approach as the E165 shebang fix).
            wrapper_dir = os.path.join(self.build_folder, "bin")
            os.makedirs(wrapper_dir, exist_ok=True)
            for tool in ("gauche-package", "gauche-install", "gauche-cesconv"):
                src = os.path.join(gauche_bin, tool)
                if os.path.isfile(src):
                    with open(os.path.join(wrapper_dir, tool), "w") as f:
                        f.write(f'#!/bin/sh\nexec "{gosh_path}" "{src}" "$@"\n')
                    os.chmod(os.path.join(wrapper_dir, tool), 0o755)
            env.prepend_path("PATH", wrapper_dir)
        # NOTE: AutotoolsToolchain.generate() re-creates the environment from
        # self.environment(); the customized env must be passed explicitly.
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # configure 用 gauche-package 生成 WiLiKi.gpd；但 CI 沙箱中
        # gauche 包模块符号链接悬空（指向发布机 .conan2 缓存路径），
        # gauche-package 加载 gauche.package 失败 → gpd 未生成 →
        # make install 安装 WiLiKi.gpd 时失败。此处兜底生成内容固定的
        # gpd（wiliki 为纯 Scheme 库，gpd 仅作包描述，不参与运行）。
        gpd = os.path.join(self.build_folder, "WiLiKi.gpd")
        if not os.path.isfile(gpd):
            with open(gpd, "w") as f:
                f.write(
                    ';; -*-Scheme-*-\n'
                    ';; Gauche Package Description\n\n'
                    '(define-gauche-package "WiLiKi"\n'
                    '  :repository #f\n'
                    f'  :version "{self.version}"\n'
                    '  :description #f\n'
                    '  :require ()\n'
                    '  :maintainers ()\n'
                    '  :authors ()\n'
                    '  :licenses ()\n'
                    '  :homepage #f\n'
                    '  :providing-modules ()\n'
                    '  :superseded-by #f\n'
                    '  :gauche-version "0.9.15"\n'
                    ')\n'
                )
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # wiliki installs Scheme modules into Gauche's site lib; there is no
        # C library or header to link against, and no executables are installed
        # (pure Scheme library), so nothing to declare for R38.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Consumers run wiliki through gosh; expose the site lib so a
        # downstream Gauche app can (use wiliki).
        site_lib = os.path.join("share", "gauche-0.98", "site", "lib")
        self.cpp_info.resdirs = [site_lib]
