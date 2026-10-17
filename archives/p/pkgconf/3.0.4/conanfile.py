#!/usr/bin/env python3
"""Conan recipe for pkgconf 3.0.4."""

import glob
import hashlib
import io
import json
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class PkgconfConan(ConanFile):
    name = "pkgconf"
    version = "3.0.4"
    description = "pkg-config compatible dependency metadata resolver and library"
    license = "ISC"
    homepage = "https://github.com/pkgconf/pkgconf"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    _UPSTREAM_TEST_NAMES = frozenset(
        {
            "api-audit",
            "api-buffer",
            "api-bytecode",
            "api-client",
            "api-dependency",
            "api-fileio",
            "api-fragment",
            "api-license",
            "api-oom-spdxtool",
            "api-path-utils",
            "api-personality",
            "api-queue",
            "api-serialize",
            "api-tuple",
            "api-variable",
            "api-version",
            "basic",
            "bomtool",
            "cli",
            "fuzz-replay-missing-path",
            "fuzz-replay-parser",
            "fuzz-replay-solver",
            "link-abi",
            "ordering",
            "parser",
            "pccritic",
            "personality",
            "sbom",
            "solver",
            "spdxtool",
            "symlink",
            "sysroot",
            "tuple",
        }
    )
    _UPSTREAM_FIXTURE_TEST_NAMES = frozenset(
        {
            "basic",
            "bomtool",
            "cli",
            "link-abi",
            "ordering",
            "parser",
            "pccritic",
            "personality",
            "sbom",
            "solver",
            "spdxtool",
            "symlink",
            "sysroot",
            "tuple",
        }
    )

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "pkgconf is packaged as a static library"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_tool(self, tool):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compiler_executables.get("c", "")
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path)
        compiler_name = os.path.basename(compiler_path)
        version_suffix = (
            compiler_name[len("clang") :]
            if compiler_name.startswith("clang")
            else ""
        )

        candidates = [compiler_executables.get(tool)]
        if compiler_dir:
            candidates.extend(
                [
                    os.path.join(compiler_dir, f"llvm-{tool}{version_suffix}"),
                    os.path.join(compiler_dir, f"llvm-{tool}"),
                    os.path.join(compiler_dir, tool),
                ]
            )
        if version_suffix:
            candidates.append(f"llvm-{tool}{version_suffix}")
        candidates.extend([f"llvm-{tool}", tool])

        for candidate in candidates:
            if candidate:
                resolved = shutil.which(candidate)
                if resolved:
                    return resolved

        raise ConanInvalidConfiguration(
            f"required LLVM archive tool was not found: {tool}"
        )

    def _find_ohos_runtime_tool(self, name):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c") or compiler_executables.get("cpp", "")
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path)
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        for candidate in candidates:
            resolved = shutil.which(candidate) or candidate
            if resolved and os.path.isfile(resolved) and not os.path.islink(resolved):
                return os.path.abspath(resolved)
        return ""

    @staticmethod
    def _file_sha256(path):
        digest = hashlib.sha256()
        with open(path, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _run_signing_tool(argv, label):
        completed = subprocess.run(
            argv,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            raise ConanException(
                f"{label} failed ({completed.returncode}): "
                f"{completed.stderr.strip()}"
            )
        return completed.stdout

    def _elf_sections(self, readelf, path):
        output = self._run_signing_tool([readelf, "-S", path], "llvm-readelf")
        if ".note.ohos.ident" not in output:
            raise ConanException(f"ELF platform identity section missing: {path}")
        return output

    def _sign_elf_atomically(self, path, objcopy, readelf, signer):
        if not os.path.isfile(path) or os.path.islink(path):
            raise ConanException(f"unsafe ELF signing input: {path}")
        with open(path, "rb") as stream:
            if stream.read(4) != b"\x7fELF":
                raise ConanException(f"signing input is not ELF: {path}")

        unsigned_sha256 = self._file_sha256(path)
        temporary = f"{path}.unsigned-for-signing"
        signed = f"{path}.signed"
        if os.path.lexists(temporary) or os.path.lexists(signed):
            raise ConanException(f"stale signing transaction beside: {path}")

        try:
            shutil.copy2(path, temporary)
            sections = self._elf_sections(readelf, temporary)
            if ".codesign" in sections:
                self._run_signing_tool(
                    [objcopy, "--remove-section", ".codesign", temporary],
                    "llvm-objcopy",
                )
                self._elf_sections(readelf, temporary)

            self._run_signing_tool(
                [
                    signer,
                    "sign",
                    "-inFile",
                    temporary,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                "binary-sign-tool",
            )
            if not os.path.isfile(signed) or os.path.islink(signed):
                raise ConanException(f"signer did not create a regular output: {path}")
            signed_sections = self._elf_sections(readelf, signed)
            if ".codesign" not in signed_sections:
                raise ConanException(f"signed ELF has no .codesign section: {path}")

            os.chmod(signed, 0o755)
            signed_sha256 = self._file_sha256(signed)
            if signed_sha256 == unsigned_sha256:
                raise ConanException(f"ELF signing did not change the file: {path}")
            os.replace(signed, path)
            self.output.info(
                f"SIGNED_ELF={os.path.basename(path)} "
                f"UNSIGNED_SHA256={unsigned_sha256} SIGNED_SHA256={signed_sha256}"
            )
        finally:
            for residue in (temporary, signed):
                if os.path.lexists(residue):
                    os.remove(residue)

    def _sign_packaged_commands(self):
        if self.settings.os != "OHOS":
            return

        tools = {
            "objcopy": self._find_ohos_runtime_tool("llvm-objcopy"),
            "readelf": self._find_ohos_runtime_tool("llvm-readelf"),
            "signer": self._find_ohos_runtime_tool("binary-sign-tool"),
        }
        missing = [name for name, path in tools.items() if not path]
        if missing:
            self.output.warning(
                "OHOS signing tools are unavailable in this cross-build environment "
                f"({', '.join(missing)}); target execution must sign task-private copies."
            )
            return

        for name in ("pkgconf", "bomtool", "spdxtool", "pccritic"):
            self._sign_elf_atomically(
                os.path.join(self.package_folder, "bin", name),
                tools["objcopy"],
                tools["readelf"],
                tools["signer"],
            )

    @staticmethod
    def _format_command(command):
        if os.name == "nt":
            return subprocess.list2cmdline(command)
        return shlex.join(command)

    def _meson_machine_args(self):
        cross = cross_building(self)
        machine_file = os.path.join(
            self.generators_folder,
            "conan_meson_cross.ini" if cross else "conan_meson_native.ini",
        )
        if not os.path.isfile(machine_file):
            raise ConanInvalidConfiguration(
                f"Meson machine file was not generated: {machine_file}"
            )
        return ["--cross-file" if cross else "--native-file", machine_file]

    def _run_meson_introspection(self, command, label):
        stdout = io.StringIO()
        stderr = io.StringIO()
        return_code = self.run(
            self._format_command(command),
            stdout=stdout,
            stderr=stderr,
            ignore_errors=True,
            env="conanbuild",
            scope="build",
        )
        if return_code != 0:
            detail = stderr.getvalue().strip() or stdout.getvalue().strip()
            raise ConanException(f"{label} failed ({return_code}): {detail}")
        return stdout.getvalue()

    def _introspect_upstream_tests(self, validation_folder):
        command = ["meson", "introspect", "--tests", validation_folder]
        output = self._run_meson_introspection(
            command, "Meson test introspection"
        )
        try:
            tests = json.loads(output)
            names = {test["name"] for test in tests}
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ConanException(f"invalid Meson test inventory: {exc}") from exc

        if len(tests) != 33 or names != self._UPSTREAM_TEST_NAMES:
            missing = sorted(self._UPSTREAM_TEST_NAMES - names)
            unexpected = sorted(names - self._UPSTREAM_TEST_NAMES)
            raise ConanException(
                "upstream test inventory mismatch: "
                f"count={len(tests)}, missing={missing}, unexpected={unexpected}"
            )
        return tests

    def _upstream_build_selectors(self, validation_folder, tests):
        command = ["meson", "introspect", validation_folder, "--targets"]
        output = self._run_meson_introspection(
            command, "Meson target introspection"
        )
        try:
            targets = json.loads(output)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ConanException(f"invalid Meson target inventory: {exc}") from exc

        dependency_ids = sorted(
            {
                dependency
                for test_record in tests
                for dependency in test_record.get("depends", [])
            }
        )
        targets_by_id = {}
        for target in targets:
            target_id = target.get("id")
            if not target_id or target_id in targets_by_id:
                raise ConanException(f"invalid or duplicate Meson target ID: {target_id}")
            targets_by_id[target_id] = target

        selectors = []
        for dependency_id in dependency_ids:
            target = targets_by_id.get(dependency_id)
            if target is None:
                raise ConanException(
                    f"missing Meson test dependency target: {dependency_id}"
                )
            name = target.get("name")
            target_type = target.get("type")
            if not name or not target_type:
                raise ConanException(
                    f"incomplete Meson test dependency target: {dependency_id}"
                )
            selectors.append(f"{name}:{target_type}")

        if len(dependency_ids) != 23 or len(set(selectors)) != 23:
            raise ConanException(
                "Meson test dependency projection mismatch: "
                f"ids={len(dependency_ids)}, selectors={len(set(selectors))}"
            )
        return selectors

    def _build_upstream_validation(self):
        validation_folder = self.build_folder + "-upstream-validation"
        if os.path.isdir(validation_folder):
            shutil.rmtree(validation_folder)

        setup = [
            "meson",
            "setup",
            validation_folder,
            self.source_folder,
            *self._meson_machine_args(),
            "--prefix=/",
            "--wrap-mode=nofallback",
            "-Ddefault_library=shared",
            "-Dlibdir=lib",
            "-Dfuzzing=false",
            "-Danalyzer=false",
            "-Dtest-reallocarray-shim=true",
        ]
        self.run(self._format_command(setup))
        tests = self._introspect_upstream_tests(validation_folder)
        build_selectors = self._upstream_build_selectors(validation_folder, tests)

        compile_tests = [
            "meson",
            "compile",
            "-C",
            validation_folder,
            "-j",
            "1",
            *build_selectors,
        ]
        self.run(self._format_command(compile_tests))
        return validation_folder

    def _verify_upstream_results(self, validation_folder):
        test_log = os.path.join(
            validation_folder, "meson-logs", "testlog.json"
        )
        try:
            with open(test_log, encoding="utf-8") as handle:
                rows = [json.loads(line) for line in handle if line.strip()]
        except (OSError, json.JSONDecodeError) as exc:
            raise ConanException(f"invalid Meson test result log: {exc}") from exc

        by_name = {row["name"].split(":", 1)[-1]: row for row in rows}
        ok_count = sum(row.get("result") == "OK" for row in rows)
        expected_fail_count = sum(
            row.get("result") == "EXPECTEDFAIL" for row in rows
        )
        if (
            len(rows) != 33
            or len(by_name) != len(rows)
            or set(by_name) != self._UPSTREAM_TEST_NAMES
            or ok_count != 32
            or expected_fail_count != 1
            or by_name["fuzz-replay-missing-path"].get("result")
            != "EXPECTEDFAIL"
        ):
            raise ConanException(
                "upstream test result mismatch: "
                f"count={len(rows)}, ok={ok_count}, "
                f"expected_fail={expected_fail_count}"
            )

        missing_corpus = by_name["fuzz-replay-missing-path"]
        if (
            missing_corpus.get("returncode") != 1
            or missing_corpus.get("stdout", "").strip() != "REPLAYED_INPUTS=0"
            or "No such file or directory" not in missing_corpus.get("stderr", "")
        ):
            raise ConanException("missing-corpus expected-failure contract mismatch")

        expected_corpora = {
            "fuzz-replay-parser": "REPLAYED_INPUTS=128",
            "fuzz-replay-solver": "REPLAYED_INPUTS=3",
        }
        for name, expected in expected_corpora.items():
            if by_name[name].get("stdout", "").strip() != expected:
                raise ConanException(
                    f"{name} replay count mismatch: "
                    + by_name[name].get("stdout", "").strip()
                )

        platform_name = "windows" if os.name == "nt" else "unix"
        expected_fixtures = {}
        fixture_pattern = os.path.join(self.source_folder, "t", "*", "*.test")
        for fixture_path in sorted(glob.glob(fixture_pattern)):
            suite = os.path.basename(os.path.dirname(fixture_path))
            fixture = os.path.basename(fixture_path)
            key = (suite, fixture)
            if key in expected_fixtures:
                raise ConanException(f"duplicate upstream fixture path: {suite}/{fixture}")
            skip_platforms = set()
            with open(fixture_path, encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("SkipPlatforms:"):
                        skip_platforms.update(line.split(":", 1)[1].split())
            expected_fixtures[key] = (
                "SKIP" if platform_name in skip_platforms else "PASS"
            )
        if len(expected_fixtures) != 394:
            raise ConanException(
                f"upstream fixture source inventory mismatch: {len(expected_fixtures)}"
            )

        fixture_terminals = {}
        for suite in sorted(self._UPSTREAM_FIXTURE_TEST_NAMES):
            for line in by_name[suite].get("stdout", "").splitlines():
                terminal, separator, fixture = line.partition(":")
                if not separator or terminal not in ("PASS", "SKIP", "FAIL"):
                    continue
                key = (suite, fixture.strip())
                if key in fixture_terminals:
                    raise ConanException(
                        f"duplicate upstream fixture terminal: {suite}/{fixture.strip()}"
                    )
                fixture_terminals[key] = terminal

        if set(fixture_terminals) != set(expected_fixtures):
            missing = sorted(set(expected_fixtures) - set(fixture_terminals))
            unexpected = sorted(set(fixture_terminals) - set(expected_fixtures))
            raise ConanException(
                "upstream fixture terminal inventory mismatch: "
                f"count={len(fixture_terminals)}, missing={missing}, "
                f"unexpected={unexpected}"
            )

        mismatched = sorted(
            (suite, fixture, expected_fixtures[(suite, fixture)], terminal)
            for (suite, fixture), terminal in fixture_terminals.items()
            if terminal != expected_fixtures[(suite, fixture)]
        )
        if mismatched:
            raise ConanException(
                f"upstream fixture terminal result mismatch: {mismatched}"
            )

    def generate(self):
        toolchain = MesonToolchain(self)
        toolchain.project_options.update(
            {
                "libdir": "lib",
                "fuzzing": False,
                "analyzer": False,
            }
        )
        toolchain.generate()

        if self.settings.os in ("Linux", "OHOS"):
            ar = self._resolve_tool("ar")
            ranlib = self._resolve_tool("ranlib")
            meson_file = os.path.join(
                self.generators_folder,
                "conan_meson_cross.ini"
                if cross_building(self)
                else "conan_meson_native.ini",
            )
            if not os.path.isfile(meson_file):
                raise ConanInvalidConfiguration(
                    f"Meson machine file was not generated: {meson_file}"
                )

            with open(meson_file, encoding="utf-8") as handle:
                content = handle.read()
            if "\nar =" not in content and "[binaries]" in content:
                archive_tools = (
                    "[binaries]\nar = '{}'\nranlib = '{}'\n".format(ar, ranlib)
                )
                content = content.replace("[binaries]\n", archive_tools, 1)
                with open(meson_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        if cross_building(self) and os.name == "nt":
            cross_file = os.path.join(
                self.generators_folder,
                "conan_meson_cross.ini",
            )
            command = [
                "meson",
                "setup",
                "--cross-file",
                cross_file,
                self.build_folder,
                self.source_folder,
                "--prefix=/",
            ]
            self.run(subprocess.list2cmdline(command))
        else:
            meson.configure()
        self.conf.define("tools.build:jobs", 1)
        meson.build()

        validation_folder = self._build_upstream_validation()

        if can_run(self):
            test_tmp = os.path.join(validation_folder, "pkgconf-test-tmp")
            os.makedirs(test_tmp, exist_ok=True)
            test_env = Environment()
            test_env.define("TMPDIR", test_tmp)
            test_env.define("MESON_TESTTHREADS", "1")
            with test_env.vars(self).apply():
                test_command = [
                    "meson",
                    "test",
                    "-C",
                    validation_folder,
                    "--print-errorlogs",
                    "--no-rebuild",
                    "--num-processes",
                    "1",
                ]
                self.run(self._format_command(test_command))
            self._verify_upstream_results(validation_folder)

            residue = glob.glob(os.path.join(test_tmp, "pkgconf-fuzz-univ-*"))
            if residue:
                raise ConanException(
                    "solver replay left temporary directories: "
                    + ", ".join(residue)
                )
            shutil.rmtree(test_tmp)
        else:
            self.output.info("UPSTREAM_TARGET_TESTS=NOT_RUN")

    def package(self):
        Meson(self).install()
        if self.settings.os not in ("Linux", "OHOS"):
            return

        required = [
            "bin/pkgconf",
            "bin/bomtool",
            "bin/spdxtool",
            "bin/pccritic",
            "lib/libpkgconf.a",
            "lib/pkgconfig/libpkgconf.pc",
            "share/aclocal/pkg.m4",
            "include/pkgconf/libpkgconf/libpkgconf.h",
            "include/pkgconf/libpkgconf/stdinc.h",
            "include/pkgconf/libpkgconf/iter.h",
            "include/pkgconf/libpkgconf/bsdstubs.h",
            "include/pkgconf/libpkgconf/libpkgconf-api.h",
        ]
        missing = [
            rel
            for rel in required
            if not os.path.isfile(os.path.join(self.package_folder, rel))
        ]
        if missing:
            raise ConanException("missing packaged artifacts: " + ", ".join(missing))

        alias = os.path.join(self.package_folder, "bin", "pkg-config")
        if os.path.lexists(alias):
            raise ConanException("unexpected pkg-config alias was installed")

        self._sign_packaged_commands()

    def package_info(self):
        self.cpp_info.libs = ["pkgconf"]
        self.cpp_info.includedirs = ["include/pkgconf"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "pkgconf")
        self.cpp_info.set_property("cmake_target_name", "pkgconf::pkgconf")
        self.cpp_info.set_property("pkg_config_name", "libpkgconf")
