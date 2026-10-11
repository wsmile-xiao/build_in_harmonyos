#!/usr/bin/env python3
"""Conan recipe for the ru-tts Russian speech synthesizer."""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


class RuTtsConan(ConanFile):
    name = "ru-tts"
    version = "6.2.3"
    description = "Russian text-to-speech synthesizer library and command-line tool"
    license = "MIT"
    homepage = "https://github.com/poretsky/ru_tts"
    url = "https://github.com/poretsky/ru_tts"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    _library_sources = (
        "synth.c",
        "sink.c",
        "transcription.c",
        "text2speech.c",
        "utterance.c",
        "time_planner.c",
        "speechrate_control.c",
        "intonator.c",
        "soundproducer.c",
        "numerics.c",
        "male.c",
        "female.c",
    )

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ru-tts supports Linux and OHOS, not {self.settings.os}"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _tool(self, language):
        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        fallback = "clang" if language == "c" else language
        return configured.get(language, fallback)

    @staticmethod
    def _llvm_tool(compiler, name):
        adjacent = os.path.join(os.path.dirname(compiler), name)
        if os.path.isfile(adjacent):
            return adjacent
        located = shutil.which(name)
        if located:
            return located
        raise ConanException(f"required LLVM tool is unavailable: {name}")

    def _run_checked(self, command):
        self.output.info("+ " + " ".join(command))
        result = subprocess.run(
            command,
            cwd=self.build_folder,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if result.stdout:
            self.output.info(result.stdout.rstrip())
        if result.returncode != 0:
            raise ConanException(
                f"command failed with rc={result.returncode}: {' '.join(command)}"
            )

    def build(self):
        apply_conandata_patches(self)
        source_dir = os.path.join(self.source_folder, "src")
        object_dir = os.path.join(self.build_folder, "obj")
        config_dir = os.path.join(self.build_folder, "config")
        os.makedirs(object_dir, exist_ok=True)
        os.makedirs(config_dir, exist_ok=True)

        save(
            self,
            os.path.join(config_dir, "config.h"),
            '#define PACKAGE_NAME "ru-tts"\n'
            '#define PACKAGE_VERSION "6.2.3"\n'
            '#define RULEX_DLL "librulexdb.so.0"\n',
        )

        cc = self._tool("c")
        flags = ["-std=gnu11", "-Wall", "-Wextra"]
        if str(self.settings.build_type) == "Debug":
            flags.extend(["-O0", "-g"])
        else:
            flags.extend(["-O2", "-DNDEBUG"])
        if self.options.get_safe("fPIC", False):
            flags.append("-fPIC")

        objects = []
        for filename in self._library_sources:
            output = os.path.join(object_dir, filename + ".o")
            self._run_checked(
                [
                    cc,
                    *flags,
                    "-I",
                    source_dir,
                    "-c",
                    os.path.join(source_dir, filename),
                    "-o",
                    output,
                ]
            )
            objects.append(output)

        if bool(self.options.shared):
            full_library = os.path.join(object_dir, "librutts.so.7.0.4")
            self._run_checked(
                [
                    cc,
                    "-shared",
                    "-Wl,-soname,librutts.so.7",
                    "-Wl,--version-script="
                    + os.path.join(source_dir, "ru_tts.vscript"),
                    *objects,
                    "-lm",
                    "-o",
                    full_library,
                ]
            )
            library = os.path.join(object_dir, "librutts.so")
            shutil.copy2(full_library, os.path.join(object_dir, "librutts.so.7"))
            shutil.copy2(full_library, library)
        else:
            library = os.path.join(object_dir, "librutts.a")
            ar = self._llvm_tool(cc, "llvm-ar")
            ranlib = self._llvm_tool(cc, "llvm-ranlib")
            self._run_checked([ar, "rcs", library, *objects])
            self._run_checked([ranlib, library])

        cli_object = os.path.join(object_dir, "ru_tts.c.o")
        self._run_checked(
            [
                cc,
                *flags,
                "-I",
                config_dir,
                "-I",
                source_dir,
                "-c",
                os.path.join(source_dir, "ru_tts.c"),
                "-o",
                cli_object,
            ]
        )
        cli = os.path.join(object_dir, "ru_tts")
        link_library = library
        link_flags = []
        if bool(self.options.shared):
            link_library = "-lrutts"
            link_flags.extend(
                ["-L", object_dir, "-Wl,-rpath,$ORIGIN/../lib"]
            )
        self._run_checked(
            [cc, cli_object, *link_flags, link_library, "-lm", "-ldl", "-o", cli]
        )

        marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "source census: no tests/check targets in v6.2.3",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, separators=(",", ":"))
        )

    def package(self):
        object_dir = os.path.join(self.build_folder, "obj")
        source_dir = os.path.join(self.source_folder, "src")
        copy(
            self,
            "ru_tts.h",
            src=source_dir,
            dst=os.path.join(self.package_folder, "include"),
        )
        if bool(self.options.shared):
            copy(
                self,
                "librutts.so*",
                src=object_dir,
                dst=os.path.join(self.package_folder, "lib"),
            )
        else:
            copy(
                self,
                "librutts.a",
                src=object_dir,
                dst=os.path.join(self.package_folder, "lib"),
            )
        copy(
            self,
            "ru_tts",
            src=object_dir,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "ru_speak",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "README*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "ru-tts"),
        )
        manpages = os.path.join(self.source_folder, "manpages")
        copy(
            self,
            "*.1",
            src=manpages,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        copy(
            self,
            "*.3",
            src=manpages,
            dst=os.path.join(self.package_folder, "share", "man", "man3"),
        )

    def package_info(self):
        self.cpp_info.libs = ["rutts"]
        self.cpp_info.system_libs = ["m", "dl"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "ru_tts")
        self.cpp_info.set_property("cmake_target_name", "ru_tts::ru_tts")
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        if bool(self.options.shared):
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
            )
