#!/usr/bin/env python3
"""Conan recipe for libbfio 20260623 (libyal).

Pure-C file I/O abstraction library (file/file-pool/memory-stream/range IO).
All libyal internal deps (libcerror/libcthreads/libcdata/libcfile/libcpath/
libcsplit/libclocale/libcnotify/libuna) are bundled standalone inside the
official release tarball; configure has no external probes -> no Conan
requires (W0 conclusion: deps "").

OHOS adaptation (inline, no patches/ files, consistent with libfsext 20260201):
  - config.guess cannot guess HarmonyOS -> explicit --build/--host triplet
    (config.sub in this release already accepts aarch64-unknown-linux-ohos)
  - configure embeds `umask 077` temp-dir creation (HMDFS-incompatible,
    E011) -> rewritten to umask 022
  - --disable-nls (no gettext/libintl dependency, E027)
  - static library (libyal family convention, --enable-static/--disable-shared)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

_LOCAL_LIBS = [
    "libcdata",
    "libcerror",
    "libcfile",
    "libclocale",
    "libcnotify",
    "libcpath",
    "libcsplit",
    "libcthreads",
    "libuna",
]

_GENERATED_FILES = [
    "configure",
    "config.guess",
    "config.sub",
    "aclocal.m4",
    "Makefile.in",
]


class LibbfioConan(ConanFile):
    name = "libbfio"
    version = "20260623"
    description = "libyal 取证家族的基础文件 I/O 抽象库（文件/文件池/内存流/范围 IO），纯 C，为上层取证格式库提供统一访问层"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/libyal/libbfio"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            filename="libbfio-alpha-20260623.tar.gz",
            strip_root=True,
            **self.conan_data["sources"],
        )

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                "--disable-nls",
                "--enable-static",
                "--disable-shared",
            ]
        )
        if str(self.settings.os) == "OHOS":
            toolchain.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-ohos",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        missing_dirs = [
            library for library in _LOCAL_LIBS
            if not os.path.isdir(os.path.join(self.source_folder, library))
        ]
        missing_files = [
            filename for filename in _GENERATED_FILES
            if not os.path.isfile(os.path.join(self.source_folder, filename))
        ]
        if missing_dirs or missing_files:
            details = []
            if missing_dirs:
                details.append(
                    "bundled libyal directories: " + ", ".join(missing_dirs)
                )
            if missing_files:
                details.append(
                    "generated Autotools files: " + ", ".join(missing_files)
                )
            raise ConanInvalidConfiguration(
                "libbfio/20260623 source is not self-contained: "
                + "; ".join(details)
                + ". Do not run synclibs.sh here: adapt missing libyal "
                "dependencies in separate library worktrees first."
            )

        autotools = Autotools(self)
        old_umask = os.umask(0o022)
        try:
            if str(self.settings.os) == "OHOS":
                configure_path = os.path.join(self.source_folder, "configure")
                with open(configure_path, encoding="utf-8") as configure_file:
                    configure_text = configure_file.read()
                if "umask 077" in configure_text:
                    with open(
                        configure_path, "w", encoding="utf-8"
                    ) as configure_file:
                        configure_file.write(
                            configure_text.replace("umask 077", "umask 022")
                        )
                os.chmod(configure_path, 0o755)
                config_shell = os.environ.get(
                    "CONFIG_SHELL", "/data/service/hnp/bin/bash"
                )
                self.run(
                    f'"{config_shell}" "{configure_path}" '
                    f"{autotools._configure_args}",
                    cwd=self.source_folder,
                )
            else:
                autotools.configure()
            # -j2: reduce parallel fork pressure (OOM observed on memory-constrained
            # builders with -j4 during concurrent local/CI compilation).
            self.run("make -j2", cwd=self.source_folder)
            if str(self.settings.os) == "OHOS":
                config_shell = os.environ.get(
                    "CONFIG_SHELL", "/data/service/hnp/bin/bash"
                )
                library_path = os.path.join(
                    self.source_folder, "libbfio", ".libs"
                )
                old_ld_library_path = os.environ.get("LD_LIBRARY_PATH")
                if old_ld_library_path:
                    os.environ["LD_LIBRARY_PATH"] = (
                        library_path + os.pathsep + old_ld_library_path
                    )
                else:
                    os.environ["LD_LIBRARY_PATH"] = library_path
                try:
                    self.run(
                        f'make -j1 check LOG_COMPILER="{config_shell}"',
                        cwd=self.source_folder,
                    )
                finally:
                    if old_ld_library_path is None:
                        os.environ.pop("LD_LIBRARY_PATH", None)
                    else:
                        os.environ["LD_LIBRARY_PATH"] = old_ld_library_path
            else:
                self.run("make -j1 check", cwd=self.source_folder)
        finally:
            os.umask(old_umask)

    def package(self):
        self.run(
            f'make install DESTDIR="{self.package_folder}"',
            cwd=self.source_folder,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "COPYING.LESSER",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["bfio"]
        self.cpp_info.set_property("cmake_file_name", "libbfio")
        self.cpp_info.set_property("cmake_target_name", "libbfio::libbfio")
        self.cpp_info.set_property("pkg_config_name", "libbfio")
