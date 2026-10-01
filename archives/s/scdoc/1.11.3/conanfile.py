#!/usr/bin/env python3
"""Conan recipe for scdoc 1.11.3."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get, load, save
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv


class ScdocConan(ConanFile):
    name = "scdoc"
    version = "1.11.3"
    description = "Simple man page generator for POSIX systems"
    license = "MIT"
    homepage = "https://git.sr.ht/~sircmpwn/scdoc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"scdoc supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        apply_conandata_patches(self)
        prebuilt_man_dir = Path(self.export_sources_folder, "man")
        if prebuilt_man_dir.is_dir():
            for filename in ("scdoc.1", "scdoc.5"):
                copy(
                    self,
                    filename,
                    src=str(prebuilt_man_dir),
                    dst=self.source_folder,
                    keep_path=False,
                )

    def export_sources(self):
        patches_dir = Path(self.recipe_folder, "patches")
        if patches_dir.is_dir():
            copy(
                self,
                "*.patch",
                src=str(patches_dir),
                dst=os.path.join(self.export_sources_folder, "patches"),
                keep_path=False,
            )
        man_dir = Path(self.recipe_folder, "man")
        if man_dir.is_dir():
            for filename in ("scdoc.1", "scdoc.5"):
                copy(
                    self,
                    filename,
                    src=str(man_dir),
                    dst=os.path.join(self.export_sources_folder, "man"),
                    keep_path=False,
                )

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        if str(self.settings.os) == "OHOS":
            self._build_target()
            host_generator_ready = self._build_host_generator()
            self._generate_man_pages(host_generator_ready)
            self._write_pkgconfig()
        else:
            self._run_make("all")
            self._run_make("check")

    def package(self):
        copy(self, "scdoc", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "scdoc.1", src=self.build_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)
        copy(self, "scdoc.5", src=self.build_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man5"), keep_path=False)
        copy(self, "scdoc.pc", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "pkgconfig"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.define_path("SCDOC_ROOT", self.package_folder)
        self.runenv_info.define_path("SCDOC_ROOT", self.package_folder)

    def _run_make(self, args):
        command = f"make {args}"
        self.run(command, cwd=self.source_folder, env="conanbuild")

    def _build_target(self):
        executables = self.conf.get("tools.build:compiler_executables", default={}) or {}
        compiler = executables.get("c")
        if not compiler:
            raise ConanException("OHOS target compiler is missing from tools.build:compiler_executables")

        cflags = self._conf_list("tools.build:cflags")
        link_flags = self._conf_list("tools.build:exelinkflags")
        sysroot = self.conf.get("tools.build:sysroot", default=None)
        if sysroot:
            cflags.append(f"--sysroot={sysroot}")
            link_flags.append(f"--sysroot={sysroot}")

        source_names = [
            "main.c", "string.c", "utf8_chsize.c", "utf8_decode.c",
            "utf8_encode.c", "utf8_fgetch.c", "utf8_fputch.c",
            "utf8_size.c", "util.c",
        ]
        object_dir = Path(self.source_folder, ".build")
        object_dir.mkdir(parents=True, exist_ok=True)
        common = [
            "-std=c99", "-pedantic", "-DVERSION=\"%s\"" % self.version,
            "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter",
            "-I", os.path.join(self.source_folder, "include"),
        ] + cflags
        objects = []
        for source_name in source_names:
            source = Path(self.source_folder, "src", source_name)
            obj = Path(object_dir, Path(source_name).stem + ".o")
            self._run_command([compiler] + common + ["-c", "-o", str(obj), str(source)])
            objects.append(str(obj))

        target = Path(self.source_folder, "scdoc")
        self._run_command([compiler] + link_flags + ["-static", "-o", str(target)] + objects)

    def _conf_list(self, name):
        values = self.conf.get(name, default=[]) or []
        if isinstance(values, str):
            return [values]
        return [str(value) for value in values]

    def _run_command(self, command):
        if os.name == "nt":
            command_line = subprocess.list2cmdline([str(item) for item in command])
        else:
            command_line = " ".join(shlex.quote(str(item)) for item in command)
            compiler_dir = Path(str(command[0])).parent
            runtime_dirs = (compiler_dir, compiler_dir.parent / "lib")
            runtime = ":".join(shlex.quote(str(path)) for path in runtime_dirs)
            command_line = f"LD_LIBRARY_PATH={runtime}:$LD_LIBRARY_PATH {command_line}"
        self.run(command_line, cwd=self.source_folder)

    def _build_host_generator(self):
        compiler = shutil.which("gcc") or shutil.which("cc")
        if not compiler:
            return False
        host_name = "scdoc-host.exe" if os.name == "nt" else "scdoc-host"
        host_binary = Path(self.build_folder, host_name)
        sources = [
            "main.c", "string.c", "utf8_chsize.c", "utf8_decode.c",
            "utf8_encode.c", "utf8_fgetch.c", "utf8_fputch.c",
            "utf8_size.c", "util.c",
        ]
        command = [
            compiler, "-std=c99", "-pedantic", "-Wall", "-Wextra",
            "-Wno-unused-parameter", f'-DVERSION="{self.version}"',
            "-I", os.path.join(self.source_folder, "include"), "-o", str(host_binary),
        ] + [os.path.join(self.source_folder, "src", item) for item in sources]
        if os.name == "nt":
            command_line = subprocess.list2cmdline([str(item) for item in command])
        else:
            command_line = " ".join(shlex.quote(str(item)) for item in command)
        self.run(command_line, cwd=self.build_folder)
        if not host_binary.is_file():
            raise ConanException(f"host scdoc generator was not created: {host_binary}")
        return True

    def _generate_man_pages(self, host_generator_ready):
        host_name = "scdoc-host.exe" if os.name == "nt" else "scdoc-host"
        host_path = str(Path(self.build_folder, host_name))
        if not host_generator_ready:
            for filename in ("scdoc.1", "scdoc.5"):
                prebuilt = Path(self.source_folder, filename)
                if not prebuilt.is_file():
                    raise ConanException(
                        f"host compiler unavailable and pre-generated {filename} is missing"
                    )
                copy(
                    self,
                    filename,
                    src=self.source_folder,
                    dst=self.build_folder,
                    keep_path=False,
                )
            return
        host = subprocess.list2cmdline([host_path]) if os.name == "nt" else shlex.quote(host_path)
        for source, output in (("scdoc.1.scd", "scdoc.1"), ("scdoc.5.scd", "scdoc.5")):
            source_path = os.path.join(self.source_folder, source)
            output_path = os.path.join(self.build_folder, output)
            source_arg = subprocess.list2cmdline([source_path]) if os.name == "nt" else shlex.quote(source_path)
            output_arg = subprocess.list2cmdline([output_path]) if os.name == "nt" else shlex.quote(output_path)
            self.run(
                f"{host} < {source_arg} > {output_arg}",
                cwd=self.build_folder,
            )

    def _write_pkgconfig(self):
        template = load(self, os.path.join(self.source_folder, "scdoc.pc.in"))
        content = template.replace("@prefix@", "/").replace("@version@", self.version)
        save(self, os.path.join(self.source_folder, "scdoc.pc"), content)
