#!/usr/bin/env python3
"""Conan recipe for xtrans 1.4.0 source-distribution package."""

import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


XTRANS_SOURCES = (
    "Xtrans.h",
    "Xtrans.c",
    "Xtransint.h",
    "Xtranslcl.c",
    "Xtranssock.c",
    "Xtransutil.c",
    "transport.c",
)


class XtransConan(ConanFile):
    name = "xtrans"
    version = "1.4.0"
    description = "Shared X.Org network transport implementation sources"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxtrans"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xtrans supports Linux and OHOS, not {self.settings.os}"
            )

    def package_id(self):
        self.info.settings.rm_safe("build_type")

    def requirements(self):
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )
        apply_conandata_patches(self)

    def generate(self):
        temp_dir = Path(self.build_folder, ".tmp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temp_dir))
        environment.vars(self).save_script("xtrans_build_env")

    def build(self):
        build_dir = Path(self.build_folder)
        build_dir.mkdir(parents=True, exist_ok=True)
        defines = ["_DEFAULT_SOURCE", "_BSD_SOURCE", "HAS_STICKY_DIR_BIT"]
        if self._has_fchown(self._c_compiler(), build_dir):
            defines.append("HAS_FCHOWN")

        (build_dir / "xtrans-defines.txt").write_text(
            "\n".join(defines) + "\n", encoding="utf-8"
        )
        define_flags = " ".join(f"-D{define}" for define in defines)
        pc_content = f"""prefix=${{pcfiledir}}/../..
exec_prefix=${{prefix}}
libdir=${{exec_prefix}}/lib
includedir=${{prefix}}/include

Name: XTrans
Description: Abstract network code for X
URL: https://gitlab.freedesktop.org/xorg/lib/libxtrans
Version: {self.version}
Cflags: -I${{includedir}} {define_flags}
"""
        (build_dir / "xtrans.pc").write_text(pc_content, encoding="utf-8")

    def package(self):
        include_dir = os.path.join(self.package_folder, "include", "X11", "Xtrans")
        for filename in XTRANS_SOURCES:
            source = Path(self.source_folder, filename)
            if not source.is_file():
                raise ConanException(f"missing upstream install input: {filename}")
            copy(
                self,
                filename,
                src=self.source_folder,
                dst=include_dir,
                keep_path=False,
            )

        copy(
            self,
            "xtrans.m4",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "aclocal"),
            keep_path=False,
        )
        copy(
            self,
            "xtrans.pc",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "share", "pkgconfig"),
            keep_path=False,
        )
        copy(
            self,
            "xtrans-defines.txt",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "share", "xtrans"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "xtrans"),
            keep_path=False,
        )
        copy(
            self,
            "xtrans.xml",
            src=os.path.join(self.source_folder, "doc"),
            dst=os.path.join(self.package_folder, "share", "doc", "xtrans"),
            keep_path=False,
        )

    def package_info(self):
        defines_path = Path(
            self.package_folder, "share", "xtrans", "xtrans-defines.txt"
        )
        if not defines_path.is_file():
            raise ConanException("xtrans consumer definitions were not packaged")
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.defines = defines_path.read_text(encoding="utf-8").splitlines()
        self.cpp_info.requires = ["xorgproto::xorgproto"]
        self.cpp_info.set_property("cmake_file_name", "xtrans")
        self.cpp_info.set_property("cmake_target_name", "xtrans::xtrans")
        pc_dir = os.path.join(self.package_folder, "share", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    def _c_compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("c")
        if not compiler:
            raise ConanException(
                "tools.build:compiler_executables must define the C compiler"
            )
        return compiler

    def _has_fchown(self, compiler, build_dir):
        source = build_dir / "fchown-probe.c"
        output = build_dir / "fchown-probe"
        source.write_text(
            "#define _DEFAULT_SOURCE 1\n"
            "#include <sys/types.h>\n"
            "#include <unistd.h>\n"
            "int main(void) {\n"
            "    int (*probe)(int, uid_t, gid_t) = fchown;\n"
            "    return probe == 0;\n"
            "}\n",
            encoding="utf-8",
        )
        result = self.run(
            f'"{compiler}" -std=c11 -Werror "{source}" -o "{output}"',
            ignore_errors=True,
            env=["conanbuild", "xtrans_build_env"],
        )
        self.output.info(f"target fchown probe exit code: {result}")
        return result == 0
