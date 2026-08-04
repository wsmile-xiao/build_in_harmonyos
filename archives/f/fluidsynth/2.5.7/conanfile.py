#!/usr/bin/env python3
"""Conan recipe for FluidSynth 2.5.7 on HarmonyOS."""

import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)


class FluidSynthConan(ConanFile):
    name = "fluidsynth"
    version = "2.5.7"
    description = "Real-time SoundFont software synthesizer"
    license = ("LGPL-2.1-or-later", "Apache-2.0")
    homepage = "https://www.fluidsynth.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    _shared_soname = "libfluidsynth.so.3"
    _shared_realname = "libfluidsynth.so.3.5.6"

    _upstream_test_targets = (
        "test_synth_reset_cc",
        "test_sample_cache",
        "test_sfont_loading",
        "test_preset_sample_loading",
        "test_preset_pinning",
        "test_bug_635",
        "test_settings_unregister_callback",
        "test_pointer_alignment",
        "test_seqbind_unregister",
        "test_synth_chorus_reverb",
        "test_snprintf",
        "test_synth_process",
        "test_ct2hz",
        "test_sample_validate",
        "test_sfont_unloading",
        "test_sfont_zone",
        "test_seq_event_queue_sort",
        "test_seq_scale",
        "test_seq_evt_order",
        "test_seq_event_queue_remove",
        "test_jack_obtaining_synth",
        "test_utf8_open",
        "test_portamento_time",
        "test_modulator",
        "test_default_mod",
        "test_ABI",
        "test_file_seek_tell",
        "test_shell_server_auto_port",
        "test_threading",
        "dump_sfont",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        gcem = self.conan_data["gcem"]
        get(
            self,
            url=gcem["url"],
            sha256=gcem["sha256"],
            destination=os.path.join(self.source_folder, "gcem"),
            strip_root=True,
        )

    def generate(self):
        toolchain = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            platform_modules = os.path.join(
                self.build_folder, "_cmake_modules"
            )
            save(
                self,
                os.path.join(
                    platform_modules, "Platform", "HarmonyOS.cmake"
                ),
                "include(Platform/Linux)\n",
            )
            toolchain.variables["CMAKE_MODULE_PATH"] = platform_modules
            if self.options.shared:
                toolchain.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = True

        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = (
            bool(self.options.shared)
            or bool(self.options.get_safe("fPIC", True))
        )
        toolchain.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        toolchain.variables["osal"] = "cpp11"
        toolchain.variables["enable-native-dls"] = True
        toolchain.variables["enable-threads"] = True

        disabled_features = (
            "enable-alsa",
            "enable-aufile",
            "enable-coverage",
            "enable-dbus",
            "enable-dsound",
            "enable-floats",
            "enable-fpe-check",
            "enable-ipv6",
            "enable-jack",
            "enable-ladspa",
            "enable-libinstpatch",
            "enable-libsndfile",
            "enable-midishare",
            "enable-network",
            "enable-oboe",
            "enable-openmp",
            "enable-opensles",
            "enable-oss",
            "enable-pipewire",
            "enable-portaudio",
            "enable-profiling",
            "enable-pulseaudio",
            "enable-readline",
            "enable-sdl3",
            "enable-trap-on-fpe",
            "enable-ubsan",
            "enable-unicode",
            "enable-wasapi",
            "enable-waveout",
            "enable-winmidi",
        )
        for feature in disabled_features:
            toolchain.variables[feature] = False
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        if (
            self.settings.os == "OHOS"
            and self.options.shared
            and can_run(self)
        ):
            cmake.build(target="libfluidsynth", build_tool_args=["-j1"])
            self._prepare_ohos_shared_library()
        elif self.settings.os == "OHOS" and self.options.shared:
            self.output.info(
                "NOT_RUN FLUIDSYNTH_BUILD_SONAME_PREP=0/1 "
                "reason=cross_building"
            )
        cmake.build(build_tool_args=["-j1"])
        if can_run(self):
            if self.settings.os == "OHOS":
                self._build_and_sign_upstream_tests(cmake)
            cmake.build(target="check", build_tool_args=["-j1"])
            self.output.info("FLUIDSYNTH_UPSTREAM_TESTS=30/30")
        else:
            self.output.info(
                "NOT_RUN FLUIDSYNTH_UPSTREAM_TESTS=0/30 "
                "reason=cross_building"
            )

    def package(self):
        CMake(self).install()
        self._fix_static_pkg_config()
        self._sign_package_elfs_for_ohos()
        self._materialize_ohos_shared_aliases()
        fluidsynth_licenses = copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        gcem_licenses = copy(
            self,
            "LICENSE",
            src=os.path.join(self.source_folder, "gcem"),
            dst=os.path.join(self.package_folder, "licenses", "gcem"),
            keep_path=False,
        )
        gcem_notices = copy(
            self,
            "NOTICE.txt",
            src=os.path.join(self.source_folder, "gcem"),
            dst=os.path.join(self.package_folder, "licenses", "gcem"),
            keep_path=False,
        )
        license_counts = tuple(
            map(len, (fluidsynth_licenses, gcem_licenses, gcem_notices))
        )
        if license_counts != (1, 1, 1):
            raise ConanInvalidConfiguration(
                "incomplete license package: expected FluidSynth LICENSE plus "
                f"GCEM LICENSE and NOTICE.txt; got {license_counts}"
            )

    def _fix_static_pkg_config(self):
        if self.settings.os != "OHOS" or self.options.shared:
            return

        pc_file = os.path.join(
            self.package_folder, "lib", "pkgconfig", "fluidsynth.pc"
        )
        if not os.path.isfile(pc_file):
            raise ConanInvalidConfiguration(
                f"installed FluidSynth pkg-config file is missing: {pc_file}"
            )

        with open(pc_file, encoding="utf-8") as stream:
            lines = stream.read().splitlines()
        private_fields = [
            index
            for index, line in enumerate(lines)
            if line.startswith("Libs.private:")
        ]
        if len(private_fields) != 1:
            raise ConanInvalidConfiguration(
                "fluidsynth.pc must contain exactly one Libs.private field"
            )

        index = private_fields[0]
        private_libs = shlex.split(lines[index].split(":", 1)[1])
        required_libs = ("-lm", "-lpthread", "-lc++")
        private_libs.extend(
            library for library in required_libs if library not in private_libs
        )
        lines[index] = "Libs.private: " + " ".join(private_libs)
        save(self, pc_file, "\n".join(lines) + "\n")
        self.output.info("FLUIDSYNTH_STATIC_PKGCONFIG_LIBS=3/3")

    def _prepare_ohos_shared_library(self):
        library = os.path.join(self.build_folder, "src", "libfluidsynth.so")
        patchelf = "/data/service/hnp/bin/patchelf"
        if not os.path.isfile(patchelf):
            raise ConanInvalidConfiguration(
                f"HarmonyOS patchelf is missing: {patchelf}"
            )
        if not self._is_elf(library):
            raise ConanInvalidConfiguration(
                f"FluidSynth shared library is missing or invalid: {library}"
            )

        self.run(
            f"{shlex.quote(patchelf)} --set-soname "
            f"{shlex.quote(self._shared_soname)} {shlex.quote(library)}"
        )
        self._sign_elf_for_ohos(library)

        soname_alias = os.path.join(self.build_folder, "src", self._shared_soname)
        shutil.copy2(library, soname_alias)
        if os.path.islink(soname_alias) or not self._is_elf(soname_alias):
            raise ConanInvalidConfiguration(
                f"FluidSynth build-tree SONAME alias is invalid: {soname_alias}"
            )
        self.output.info("FLUIDSYNTH_BUILD_SONAME_ALIAS=1/1")

    def _materialize_ohos_shared_aliases(self):
        if self.settings.os != "OHOS" or not self.options.shared:
            return

        library_dir = os.path.join(self.package_folder, "lib")
        library = os.path.join(library_dir, "libfluidsynth.so")
        if not self._is_elf(library):
            raise ConanInvalidConfiguration(
                f"installed FluidSynth shared library is invalid: {library}"
            )

        aliases = (self._shared_soname, self._shared_realname)
        for filename in aliases:
            alias = os.path.join(library_dir, filename)
            shutil.copy2(library, alias)
            if os.path.islink(alias) or not self._is_elf(alias):
                raise ConanInvalidConfiguration(
                    f"installed FluidSynth shared alias is invalid: {alias}"
                )
        self.output.info(f"FLUIDSYNTH_PACKAGE_SHARED_ALIASES={len(aliases)}/2")

    def _build_and_sign_upstream_tests(self, cmake):
        for target in self._upstream_test_targets:
            cmake.build(target=target, build_tool_args=["-j1"])

        test_folder = os.path.join(self.build_folder, "test")
        for target in self._upstream_test_targets:
            if target == "dump_sfont":
                path = os.path.join(test_folder, "utils", target)
            else:
                path = os.path.join(test_folder, target)
            self._sign_elf_for_ohos(path)
        self.output.info("FLUIDSYNTH_UPSTREAM_TEST_ELFS_SIGNED=30/30")

    def _sign_package_elfs_for_ohos(self):
        if self.settings.os != "OHOS":
            return

        expected = 2 if self.options.shared else 1
        if not can_run(self):
            self.output.info(
                "NOT_RUN FLUIDSYNTH_PACKAGE_ELFS_SIGNED="
                f"0/{expected} reason=cross_building"
            )
            return

        signed = set()
        for directory in ("bin", "lib"):
            root_dir = os.path.join(self.package_folder, directory)
            if not os.path.isdir(root_dir):
                continue
            for root, _, files in os.walk(root_dir):
                for filename in files:
                    path = os.path.join(root, filename)
                    if os.path.islink(path) or not self._is_elf(path):
                        continue
                    real_path = os.path.realpath(path)
                    if real_path in signed:
                        continue
                    self._sign_elf_for_ohos(real_path)
                    signed.add(real_path)

        if len(signed) != expected:
            raise ConanInvalidConfiguration(
                "unexpected installed ELF count: "
                f"signed={len(signed)} expected={expected}"
            )
        self.output.info(
            f"FLUIDSYNTH_PACKAGE_ELFS_SIGNED={len(signed)}/{expected}"
        )

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_elf_for_ohos(self, path):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        readelf = "/data/service/hnp/bin/llvm-readelf"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        missing = [
            tool for tool in (objcopy, readelf, signer) if not os.path.isfile(tool)
        ]
        if missing:
            raise ConanInvalidConfiguration(
                "HarmonyOS ELF signing tools are missing: " + ", ".join(missing)
            )
        if not self._is_elf(path):
            raise ConanInvalidConfiguration(f"ELF signing input is invalid: {path}")

        clean_path = f"{path}.fluidsynth-codesign-clean"
        signed_path = f"{path}.fluidsynth-signed"
        for temporary in (clean_path, signed_path):
            if os.path.exists(temporary):
                os.remove(temporary)
        try:
            self.run(
                f"{shlex.quote(objcopy)} --remove-section .codesign "
                f"{shlex.quote(path)} {shlex.quote(clean_path)}"
            )
            self.run(
                f"{shlex.quote(signer)} sign -inFile {shlex.quote(clean_path)} "
                f"-outFile {shlex.quote(signed_path)} -selfSign 1"
            )
            sections = subprocess.run(
                [readelf, "-SW", signed_path],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            ).stdout.splitlines()
            count = sum(".codesign" in line.split() for line in sections)
            if count != 1:
                raise ConanInvalidConfiguration(
                    f"signed ELF has {count} .codesign sections: {path}"
                )
            os.replace(signed_path, path)
            os.chmod(path, 0o755)
        finally:
            for temporary in (clean_path, signed_path):
                if os.path.exists(temporary):
                    os.remove(temporary)

    def package_info(self):
        self.cpp_info.libs = ["fluidsynth"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "FluidSynth")
        self.cpp_info.set_property(
            "cmake_target_name", "FluidSynth::libfluidsynth"
        )
        self.cpp_info.set_property("pkg_config_name", "fluidsynth")
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
            if str(self.settings.compiler) == "gcc":
                self.cpp_info.system_libs.append("stdc++")
            elif str(self.settings.compiler) in ("apple-clang", "clang"):
                self.cpp_info.system_libs.append("c++")
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
