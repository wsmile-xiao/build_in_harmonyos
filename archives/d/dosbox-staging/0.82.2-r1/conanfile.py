#!/usr/bin/env python3
"""Conan recipe for DOSBox Staging 0.82.2-r1."""

import json
import os
import posixpath
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class DosboxStagingConan(ConanFile):
    name = "dosbox-staging"
    version = "0.82.2-r1"
    description = "Modern DOS emulator focused on accuracy and usability"
    license = "GPL-2.0-or-later"
    homepage = "https://www.dosbox-staging.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    _source_git_hash = "f8c24"
    _upstream_tests = (
        "gtest example",
        "gtest fs_utils",
        "gtest program_mixer",
        "gtest ansi_code_markup",
        "gtest batch_file",
        "gtest bit_view",
        "gtest bitops",
        "gtest cmd_move",
        "gtest dos_files",
        "gtest drives",
        "gtest fraction",
        "gtest int10_modes",
        "gtest iohandler_containers",
        "gtest math_utils",
        "gtest mixer",
        "gtest rect",
        "gtest ring_buffer",
        "gtest rgb",
        "gtest rwqueue",
        "gtest setup",
        "gtest shell_cmds",
        "gtest shell_redirection",
        "gtest string_utils",
        "gtest support",
    )
    _upstream_expected_results = {"gtest example": "EXPECTEDFAIL"}
    _ohos_directive = re.compile(
        rb"^[+\- ]?[ \t]*#[ \t]*(?:if|ifdef|ifndef|elif|define|undef)\b"
        rb"[^\r\n]*OHOS",
        re.IGNORECASE,
    )
    _c_cpp_suffixes = (
        ".c",
        ".cc",
        ".cpp",
        ".cxx",
        ".h",
        ".hh",
        ".hpp",
        ".hxx",
        ".h.in",
        ".hpp.in",
        ".inc",
        ".inl",
        ".ipp",
        ".tpp",
        ".m",
        ".mm",
        ".s",
        ".asm",
    )

    def export_sources(self):
        self._assert_no_ohos_directives(
            os.path.join(self.recipe_folder, "patches"),
            "archive patches",
        )
        export_conandata_patches(self)

    def requirements(self):
        self.requires("iir1/1.10.0", options={"shared": True})
        self.requires("opusfile/0.12", options={"shared": True})
        self.requires("libogg/1.3.5")
        # SDL_net 2.2.0's published recipe still names SDL 2.30.10, while
        # its public component links only the stable SDL2 API.  Force the
        # validated native-backend provider so the consumer is built and
        # exercised against SDL2 2.32.10.
        self.requires("sdl2/2.32.10", override=True)
        self.requires("zlib/1.3.2")
        self.requires("libpng/1.6.58.2", options={"shared": True})
        self.requires("speexdsp/1.2.1")
        self.requires("sdl2_net/2.2.0.1")
        self.requires("libslirp/4.9.3", options={"shared": True})
        self.requires("fluidsynth/2.5.7", options={"shared": True})
        self.requires("mt32emu/2.7.1", options={"shared": True})

    def layout(self):
        basic_layout(self)

    def _dependency_pkgconfig_repair(
        self,
        dependency_name,
        header,
        fallback_parts,
        library,
        required_pkgconfigs=(),
    ):
        dependency = self.dependencies[dependency_name]
        package_folder = dependency.package_folder
        if not package_folder or not os.path.isabs(package_folder):
            raise ConanInvalidConfiguration(
                f"{dependency_name} dependency does not expose an absolute "
                "package folder"
            )
        metadata_records = [dependency.cpp_info]
        metadata_records.extend(dependency.cpp_info.components.values())
        for metadata in metadata_records:
            includedirs = [
                directory
                if os.path.isabs(directory)
                else os.path.join(package_folder, directory)
                for directory in metadata.includedirs
            ]
            valid_include = next(
                (
                    directory
                    for directory in includedirs
                    if os.path.isfile(os.path.join(directory, header))
                ),
                None,
            )
            if valid_include is None or library not in metadata.libs:
                continue
            # A complete package metadata record can still omit a public
            # pkg-config edge required by a transitive header dependency.
            if not required_pkgconfigs:
                return None
            return {
                "dependency": dependency_name,
                "package_folder": package_folder,
                "include_directory": valid_include,
                "library": library,
                "required_pkgconfigs": tuple(required_pkgconfigs),
                "version": str(dependency.ref.version),
            }

        fallback = os.path.join(package_folder, *fallback_parts)
        if not os.path.isfile(os.path.join(fallback, header)):
            raise ConanInvalidConfiguration(
                f"{dependency_name} dependency does not expose a usable "
                f"{header} include directory"
            )
        library_paths = tuple(
            os.path.join(package_folder, "lib", f"lib{library}{suffix}")
            for suffix in (".so", ".a")
        )
        if not any(os.path.isfile(path) for path in library_paths):
            raise ConanInvalidConfiguration(
                f"{dependency_name} dependency does not expose any of "
                + ", ".join(library_paths)
            )
        return {
            "dependency": dependency_name,
            "package_folder": package_folder,
            "include_directory": fallback,
            "library": library,
            "required_pkgconfigs": tuple(required_pkgconfigs),
            "version": str(dependency.ref.version),
        }

    @staticmethod
    def _rewrite_pkgconfig_contract(content, repair):
        if content.startswith("\ufeff") or "\r" in content or "\0" in content:
            raise ConanInvalidConfiguration(
                f"{repair['dependency']}.pc has invalid text encoding"
            )
        if not content.endswith("\n"):
            raise ConanInvalidConfiguration(
                f"{repair['dependency']}.pc lacks a terminal newline"
            )
        lines = content[:-1].split("\n")

        def unique_line(prefix):
            indexes = [
                index for index, line in enumerate(lines) if line.startswith(prefix)
            ]
            if len(indexes) != 1:
                raise ConanInvalidConfiguration(
                    f"{repair['dependency']}.pc requires one {prefix!r} field"
                )
            return indexes[0]

        prefix_index = unique_line("prefix=")
        includedir_index = unique_line("includedir=")
        name_index = unique_line("Name: ")
        version_index = unique_line("Version: ")
        libs_index = unique_line("Libs: ")
        cflags_index = unique_line("Cflags: ")

        package_folder = repair["package_folder"].replace("\\", "/")
        include_directory = repair["include_directory"].replace("\\", "/")
        relative_include = posixpath.relpath(include_directory, package_folder)
        if relative_include.startswith("../") or relative_include == "..":
            raise ConanInvalidConfiguration(
                f"{repair['dependency']} include directory escapes its package"
            )
        if lines[prefix_index] != f"prefix={package_folder}":
            raise ConanInvalidConfiguration(
                f"{repair['dependency']}.pc prefix differs"
            )
        if lines[name_index] != f"Name: {repair['dependency']}":
            raise ConanInvalidConfiguration(
                f"{repair['dependency']}.pc name differs"
            )
        if lines[version_index] != f"Version: {repair['version']}":
            raise ConanInvalidConfiguration(
                f"{repair['dependency']}.pc version differs"
            )
        if lines[cflags_index] != 'Cflags: -I"${includedir}"':
            raise ConanInvalidConfiguration(
                f"{repair['dependency']}.pc Cflags contract differs"
            )

        required_pkgconfigs = repair["required_pkgconfigs"]
        if required_pkgconfigs:
            requires_index = unique_line("Requires: ")
            requires = lines[requires_index].removeprefix("Requires: ").split()
            if len(requires) != len(set(requires)):
                raise ConanInvalidConfiguration(
                    f"{repair['dependency']}.pc duplicates Requires entries"
                )
            if tuple(requires) != (*required_pkgconfigs, "opus"):
                raise ConanInvalidConfiguration(
                    f"{repair['dependency']}.pc Requires contract differs"
                )

        library_flag = f"-l{repair['library']}"
        lib_tokens = lines[libs_index].split()
        if lib_tokens.count(library_flag) > 1:
            raise ConanInvalidConfiguration(
                f"{repair['dependency']}.pc duplicates {library_flag}"
            )
        if library_flag not in lib_tokens:
            lines[libs_index] += f" {library_flag}"
        lines[includedir_index] = f"includedir=${{prefix}}/{relative_include}"
        return "\n".join(lines) + "\n"

    def _repair_generated_pkgconfig_contract(self, repair):
        if repair is None:
            return
        path = os.path.join(
            self.generators_folder,
            f"{repair.get('pkg_config_name', repair['dependency'])}.pc",
        )
        if not os.path.isfile(path) or os.path.islink(path):
            raise ConanInvalidConfiguration(
                f"generated pkg-config file differs: {path}"
            )
        for name in repair["required_pkgconfigs"]:
            required_path = os.path.join(self.generators_folder, f"{name}.pc")
            if not os.path.isfile(required_path) or os.path.islink(required_path):
                raise ConanInvalidConfiguration(
                    f"generated required pkg-config file differs: {required_path}"
                )
        with open(path, encoding="utf-8", errors="strict", newline="") as handle:
            content = handle.read()
        repaired = self._rewrite_pkgconfig_contract(content, repair)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(repaired)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )
        apply_conandata_patches(self)
        self._assert_no_ohos_directives(
            self.source_folder,
            "patched C/C++ source",
            suffixes=self._c_cpp_suffixes,
        )

        framework = self.conan_data["test_framework"]
        package_cache = os.path.join(
            self.source_folder, "subprojects", "packagecache"
        )
        os.makedirs(package_cache, exist_ok=True)
        self._download_framework_file(
            framework["source_url"],
            os.path.join(package_cache, framework["source_filename"]),
            framework["source_sha256"],
        )
        self._download_framework_file(
            framework["patch_url"],
            os.path.join(package_cache, framework["patch_filename"]),
            framework["patch_sha256"],
        )

    @staticmethod
    def _framework_download_candidates(url):
        """Return bounded mirrors while retaining the upstream URL fallback."""
        if url.startswith("https://github.com/"):
            yield "https://gh-proxy.com/" + url, "gh-proxy.com"
            yield "https://ghproxy.net/" + url, "ghproxy.net"
        elif url.startswith("https://wrapdb.mesonbuild.com/v2/"):
            match = re.fullmatch(
                r"https://wrapdb\.mesonbuild\.com/v2/([^/]+)/get_patch",
                url,
            )
            if match:
                release = match.group(1)
                release_url = (
                    "https://github.com/mesonbuild/wrapdb/releases/download/"
                    f"{release}/{release}_patch.zip"
                )
                yield "https://ghproxy.net/" + release_url, "ghproxy.net"
        yield url, "official"

    def _download_framework_file(self, url, destination, sha256):
        """Download a framework file through bounded, hash-verified candidates."""
        failures = []
        for candidate_url, label in self._framework_download_candidates(url):
            try:
                download(self, candidate_url, destination, sha256=sha256)
                return
            except Exception as error:
                failures.append(f"{label}: {error}")
                if os.path.isfile(destination) and not os.path.islink(destination):
                    os.unlink(destination)
        raise ConanException(
            "Unable to download test framework from the approved candidates: "
            + "; ".join(failures)
        )

    def generate(self):
        sdl2_repair = self._dependency_pkgconfig_repair(
            "sdl2", "SDL.h", ("include", "SDL2"), "SDL2"
        )
        sdl2_net_repair = self._dependency_pkgconfig_repair(
            "sdl2_net", "SDL_net.h", ("include", "SDL2"), "SDL2_net"
        )
        if sdl2_net_repair is not None:
            sdl2_net_repair["pkg_config_name"] = "SDL2_net"
        opusfile_repair = self._dependency_pkgconfig_repair(
            "opusfile",
            "opusfile.h",
            ("include", "opus"),
            "opusfile",
            required_pkgconfigs=("ogg",),
        )
        pkgconfig = PkgConfigDeps(self)
        pkgconfig.set_property("libogg", "pkg_config_name", "ogg")
        pkgconfig.set_property("sdl2_net", "pkg_config_name", "SDL2_net")
        pkgconfig.generate()
        self._repair_generated_pkgconfig_contract(sdl2_repair)
        self._repair_generated_pkgconfig_contract(sdl2_net_repair)
        self._repair_generated_pkgconfig_contract(opusfile_repair)
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

        toolchain = MesonToolchain(self)
        if str(self.settings.os) == "OHOS":
            toolchain.binaries["ar"] = self._ohos_meson_archiver()
            compiler_executables = self.conf.get(
                "tools.build:compiler_executables",
                default={},
                check_type=dict,
            ) or {}
            compiler = compiler_executables.get("c")
            if not compiler or not posixpath.isabs(compiler):
                raise ConanInvalidConfiguration(
                    "OHOS Meson builds require an absolute POSIX C compiler path"
                )
            sdk_library_dir = posixpath.normpath(
                posixpath.join(
                    posixpath.dirname(compiler),
                    "..",
                    "sysroot",
                    "usr",
                    "lib",
                    "aarch64-linux-ohos",
                )
            )
            native_image_link_args = [f"-L{sdk_library_dir}", "-lnative_image"]
            # MesonToolchain serializes language-specific linker arguments;
            # the generic link_args field is not emitted in the final link.
            toolchain.c_link_args.extend(native_image_link_args)
            toolchain.cpp_link_args.extend(native_image_link_args)
            toolchain.c_args.append(
                "-DDOSBOX_STAGING_CAPABILITY_NATIVE_BACKEND=1"
            )
            toolchain.cpp_args.append(
                "-DDOSBOX_STAGING_CAPABILITY_NATIVE_BACKEND=1"
            )
        toolchain.cpp_std = "c++20"
        toolchain.project_options["wrap_mode"] = "nodownload"
        toolchain.project_options["use_sdl2_net"] = True
        toolchain.project_options["use_slirp"] = True
        toolchain.project_options["use_fluidsynth"] = True
        toolchain.project_options["use_mt32emu"] = True
        toolchain.project_options["use_opengl"] = False
        toolchain.project_options["use_alsa"] = "false"
        toolchain.project_options["use_xinput2"] = "false"
        toolchain.project_options["use_zlib_ng"] = ["false"]
        toolchain.project_options["tracy"] = False
        toolchain.project_options["pagesize"] = 4096
        toolchain.project_options["b_pie"] = True
        toolchain.project_options["unit_tests"] = (
            "enabled" if can_run(self) else "disabled"
        )
        toolchain.generate()

    def _ohos_meson_archiver(self):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        archiver = executables.get("ar")
        if not archiver:
            compiler = executables.get("c")
            if not compiler or not posixpath.isabs(compiler):
                raise ConanInvalidConfiguration(
                    "OHOS Meson builds require an absolute POSIX C compiler path"
                )
            archiver = posixpath.join(posixpath.dirname(compiler), "llvm-ar")
        if not posixpath.isabs(archiver):
            raise ConanInvalidConfiguration(
                "OHOS Meson builds require an absolute POSIX archiver path"
            )
        return archiver

    @classmethod
    def _assert_no_ohos_directives(cls, root, label, suffixes=None):
        violations = []
        if not os.path.isdir(root):
            raise ConanException(f"Missing {label} directory: {root}")

        for current_root, directories, filenames in os.walk(root):
            directories.sort()
            for filename in sorted(filenames):
                if suffixes and not filename.lower().endswith(suffixes):
                    continue
                path = os.path.join(current_root, filename)
                with open(path, "rb") as handle:
                    for line_number, line in enumerate(handle, 1):
                        if cls._ohos_directive.search(line):
                            relative = os.path.relpath(path, root).replace(
                                os.sep, "/"
                            )
                            violations.append(f"{relative}:{line_number}")

        if violations:
            raise ConanException(
                f"Forbidden OHOS preprocessor directive in {label}: "
                + ", ".join(violations)
            )

    def build(self):
        if str(self.settings.os) == "OHOS":
            archiver = self._ohos_meson_archiver()
            if not os.path.isfile(archiver) or not os.access(archiver, os.X_OK):
                raise ConanInvalidConfiguration(
                    f"OHOS Meson archiver is missing or not executable: {archiver}"
                )
        environment = Environment()
        environment.define("DOSBOX_SOURCE_GIT_HASH", self._source_git_hash)
        with environment.vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            if can_run(self):
                self._run_upstream_tests(meson)
            else:
                self.output.warning(
                    "NOT_RUN DOSBOX_UPSTREAM_TESTS=0/24 reason=cross_building"
                )

    def _run_upstream_tests(self, meson):
        tests = self._introspect_tests()
        discovered = tuple(item["name"] for item in tests)
        if len(discovered) != len(set(discovered)):
            raise ConanException(
                f"Duplicate upstream Meson test names: {discovered!r}"
            )
        if set(discovered) != set(self._upstream_tests):
            raise ConanException(
                "Upstream Meson test inventory mismatch: "
                f"expected={self._upstream_tests!r} actual={discovered!r}"
            )

        if str(self.settings.os) == "OHOS":
            for item in tests:
                command = item.get("cmd") or []
                if not command or not os.path.isfile(command[0]):
                    raise ConanException(
                        f"Upstream test executable is missing: {item['name']}"
                    )
                self._sign_ohos_elf(command[0])

        logbase = "dosbox-upstream"
        meson_bin = shutil.which("meson")
        if not meson_bin:
            raise ConanInvalidConfiguration("Meson executable is missing")
        command = [
            meson_bin,
            "test",
            "-C",
            self.build_folder,
            "--no-rebuild",
            "--print-errorlogs",
            "--num-processes",
            "1",
            "--logbase",
            logbase,
        ]
        with VirtualRunEnv(self).vars().apply():
            completed = subprocess.run(
                command,
                check=False,
                timeout=7200,
            )
        self._validate_test_log(logbase)
        if completed.returncode != 0:
            raise ConanException(
                f"Meson upstream tests exited with {completed.returncode}"
            )

    @classmethod
    def _normalize_terminal_name(cls, raw_name):
        if raw_name in cls._upstream_tests:
            return raw_name
        if not isinstance(raw_name, str):
            return None
        prefix = "dosbox-staging:"
        if raw_name.startswith(prefix):
            candidate = raw_name[len(prefix) :]
            if candidate in cls._upstream_tests:
                return candidate
        return None

    @classmethod
    def _terminal_results(cls, records):
        terminals = {}
        for record in records:
            if not isinstance(record, dict):
                raise ConanException("Meson JSON test record is not an object")
            raw_name = record.get("name")
            name = cls._normalize_terminal_name(raw_name)
            if name is None:
                raise ConanException(f"Unknown Meson terminal record: {raw_name!r}")
            if name in terminals:
                raise ConanException(f"Duplicate Meson terminal record: {name}")
            terminals[name] = record.get("result")

        if len(terminals) != len(cls._upstream_tests):
            raise ConanException(
                "Meson terminal count mismatch: "
                f"expected={len(cls._upstream_tests)} actual={len(terminals)}"
            )
        if set(terminals) != set(cls._upstream_tests):
            raise ConanException(
                "Meson terminal inventory mismatch: "
                f"expected={cls._upstream_tests!r} actual={tuple(terminals)!r}"
            )
        unexpected = {
            name: result
            for name, result in terminals.items()
            if result != cls._upstream_expected_results.get(name, "OK")
        }
        if unexpected:
            raise ConanException(f"Unexpected upstream test terminals: {unexpected}")
        return terminals

    def _introspect_tests(self):
        meson_bin = shutil.which("meson")
        if not meson_bin:
            raise ConanInvalidConfiguration("Meson executable is missing")
        completed = subprocess.run(
            [meson_bin, "introspect", "--tests", self.build_folder],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        if completed.returncode != 0:
            raise ConanException(
                "Meson test introspection failed:\n"
                + completed.stdout
                + completed.stderr
            )
        data = json.loads(completed.stdout)
        if not isinstance(data, list):
            raise ConanException("Meson test introspection did not return a list")
        return data

    def _validate_test_log(self, logbase):
        log_path = os.path.join(
            self.build_folder, "meson-logs", f"{logbase}.json"
        )
        if not os.path.isfile(log_path):
            raise ConanException(f"Meson JSON test log is missing: {log_path}")

        records = []
        with open(log_path, encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as error:
                    raise ConanException(
                        f"Invalid Meson JSON record at line {line_number}: {error}"
                    ) from error

        terminals = self._terminal_results(records)
        for name in self._upstream_tests:
            self.output.info(f"UPSTREAM_TEST_STATUS|{name}|{terminals[name]}")

    def package(self):
        environment = Environment()
        environment.define("DOSBOX_SOURCE_GIT_HASH", self._source_git_hash)
        with environment.vars(self).apply():
            Meson(self).install()
        executable = os.path.join(self.package_folder, "bin", "dosbox")
        if not os.path.isfile(executable):
            raise ConanException(f"Packaged executable is missing: {executable}")
        if str(self.settings.os) == "OHOS":
            if not can_run(self):
                raise ConanInvalidConfiguration(
                    "OHOS application packages must be built where signing tools run"
                )
            # Meson install may rewrite ELF metadata after build-time signing;
            # re-sign the installed bytes rather than trusting the old section.
            self._sign_ohos_elf(executable, force=True)
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    @staticmethod
    def _codesign_count(section_text):
        return sum(
            1
            for line in section_text.splitlines()
            if re.search(r"\]\s+\.codesign\s", line)
        )

    def _sign_ohos_elf(self, path, *, force=False):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        compiler = executables.get("c")
        if not compiler or not posixpath.isabs(compiler):
            raise ConanInvalidConfiguration(
                "OHOS ELF signing requires an absolute configured C compiler"
            )
        tool_directory = posixpath.dirname(compiler)
        objcopy = posixpath.join(tool_directory, "llvm-objcopy")
        readelf = posixpath.join(tool_directory, "llvm-readelf")
        signer = shutil.which("binary-sign-tool")
        for tool in (objcopy, readelf, signer):
            if not tool or not os.path.isfile(tool) or not os.access(tool, os.X_OK):
                raise ConanInvalidConfiguration(
                    f"Required OHOS ELF signing tool is missing: {tool}"
                )
        if not os.path.isfile(path):
            raise ConanException(f"ELF signing input is missing: {path}")

        existing = subprocess.run(
            [readelf, "-SW", path],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        count = self._codesign_count(existing)
        if count == 1 and not force:
            os.chmod(path, (os.stat(path).st_mode & 0o777) | 0o755)
            return
        if count not in (0, 1):
            raise ConanException(f"ELF has invalid .codesign count: {path}")

        clean = path + ".dosbox-sign-clean"
        signed = path + ".dosbox-signed"
        for temporary in (clean, signed):
            if os.path.exists(temporary):
                os.remove(temporary)
        try:
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", path, clean],
                check=True,
                timeout=30,
            )
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    clean,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                check=True,
                timeout=60,
            )
            sections = subprocess.run(
                [readelf, "-SW", signed],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
            if self._codesign_count(sections) != 1:
                raise ConanException(
                    f"Signed ELF does not have exactly one .codesign: {path}"
                )
            os.chmod(signed, (os.stat(path).st_mode & 0o777) | 0o755)
            os.replace(signed, path)
        finally:
            for temporary in (clean, signed):
                if os.path.exists(temporary):
                    os.remove(temporary)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
