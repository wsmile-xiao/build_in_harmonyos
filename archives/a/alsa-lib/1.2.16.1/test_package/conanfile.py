#!/usr/bin/env python3
"""Independent ALSA consumers plus public-ABI compile/link probes."""

import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMakeDeps
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.gnu import PkgConfigDeps


ABI_PROBES = (
    ("AL-ABI-001", "snd_asoundlib_version", "alsa/global.h"),
    ("AL-ABI-002", "snd_strerror", "alsa/error.h"),
    ("AL-ABI-003", "snd_lib_error_set_handler", "alsa/error.h"),
    ("AL-ABI-004", "snd_input_stdio_open", "alsa/input.h"),
    ("AL-ABI-005", "snd_input_stdio_attach", "alsa/input.h"),
    ("AL-ABI-006", "snd_input_buffer_open", "alsa/input.h"),
    ("AL-ABI-007", "snd_input_close", "alsa/input.h"),
    ("AL-ABI-008", "snd_input_gets", "alsa/input.h"),
    ("AL-ABI-009", "snd_output_stdio_open", "alsa/output.h"),
    ("AL-ABI-010", "snd_output_stdio_attach", "alsa/output.h"),
    ("AL-ABI-011", "snd_output_buffer_open", "alsa/output.h"),
    ("AL-ABI-012", "snd_output_close", "alsa/output.h"),
    ("AL-ABI-013", "snd_output_printf", "alsa/output.h"),
    ("AL-ABI-014", "snd_config_top", "alsa/conf.h"),
    ("AL-ABI-015", "snd_config_load_string", "alsa/conf.h"),
    ("AL-ABI-016", "snd_config_save", "alsa/conf.h"),
    ("AL-ABI-017", "snd_config_search", "alsa/conf.h"),
    ("AL-ABI-018", "snd_config_copy", "alsa/conf.h"),
    ("AL-ABI-019", "snd_config_delete", "alsa/conf.h"),
    ("AL-ABI-020", "snd_config_imake_integer", "alsa/conf.h"),
    ("AL-ABI-021", "snd_config_imake_string", "alsa/conf.h"),
    ("AL-ABI-022", "snd_ctl_open", "alsa/control.h"),
    ("AL-ABI-023", "snd_ctl_close", "alsa/control.h"),
    ("AL-ABI-024", "snd_ctl_nonblock", "alsa/control.h"),
    ("AL-ABI-025", "snd_ctl_poll_descriptors_count", "alsa/control.h"),
    ("AL-ABI-026", "snd_ctl_card_info", "alsa/control.h"),
    ("AL-ABI-027", "snd_ctl_elem_list", "alsa/control.h"),
    ("AL-ABI-028", "snd_ctl_elem_info", "alsa/control.h"),
    ("AL-ABI-029", "snd_ctl_elem_read", "alsa/control.h"),
    ("AL-ABI-030", "snd_pcm_open", "alsa/pcm.h"),
    ("AL-ABI-031", "snd_pcm_close", "alsa/pcm.h"),
    ("AL-ABI-032", "snd_pcm_nonblock", "alsa/pcm.h"),
    ("AL-ABI-033", "snd_pcm_info", "alsa/pcm.h"),
    ("AL-ABI-034", "snd_pcm_state", "alsa/pcm.h"),
    ("AL-ABI-035", "snd_pcm_prepare", "alsa/pcm.h"),
    ("AL-ABI-036", "snd_pcm_start", "alsa/pcm.h"),
    ("AL-ABI-037", "snd_pcm_drop", "alsa/pcm.h"),
    ("AL-ABI-038", "snd_pcm_drain", "alsa/pcm.h"),
    ("AL-ABI-039", "snd_pcm_pause", "alsa/pcm.h"),
    ("AL-ABI-040", "snd_pcm_writei", "alsa/pcm.h"),
    ("AL-ABI-041", "snd_pcm_readi", "alsa/pcm.h"),
    ("AL-ABI-042", "snd_pcm_recover", "alsa/pcm.h"),
    ("AL-ABI-043", "snd_pcm_format_name", "alsa/pcm.h"),
    ("AL-ABI-044", "snd_pcm_format_value", "alsa/pcm.h"),
    ("AL-ABI-045", "snd_rawmidi_open", "alsa/rawmidi.h"),
    ("AL-ABI-046", "snd_rawmidi_close", "alsa/rawmidi.h"),
    ("AL-ABI-047", "snd_rawmidi_read", "alsa/rawmidi.h"),
    ("AL-ABI-048", "snd_rawmidi_write", "alsa/rawmidi.h"),
    ("AL-ABI-049", "snd_rawmidi_drain", "alsa/rawmidi.h"),
    ("AL-ABI-050", "snd_timer_open", "alsa/timer.h"),
    ("AL-ABI-051", "snd_timer_close", "alsa/timer.h"),
    ("AL-ABI-052", "snd_timer_start", "alsa/timer.h"),
    ("AL-ABI-053", "snd_timer_stop", "alsa/timer.h"),
    ("AL-ABI-054", "snd_hwdep_open", "alsa/hwdep.h"),
    ("AL-ABI-055", "snd_hwdep_close", "alsa/hwdep.h"),
    ("AL-ABI-056", "snd_mixer_open", "alsa/mixer.h"),
    ("AL-ABI-057", "snd_mixer_close", "alsa/mixer.h"),
    ("AL-ABI-058", "snd_seq_open", "alsa/seq.h"),
    ("AL-ABI-059", "snd_seq_close", "alsa/seq.h"),
    ("AL-ABI-060", "snd_tplg_new", "alsa/topology.h"),
)

BEHAVIOR_CASES = (
    ("AL-FUN-001", "format_roundtrip.c", ("asound",)),
    ("AL-FUN-002", "areas_silence.c", ("asound",)),
    ("AL-FUN-003", "areas_copy.c", ("asound",)),
    ("AL-FUN-004", "null_playback.c", ("asound",)),
    ("AL-FUN-005", "null_capture.c", ("asound",)),
    ("AL-FUN-006", "topology_roundtrip.c", ("atopology", "asound")),
)

COMPONENT_CASES = (
    ("AL-PKG-001", "component_asound.c", ("asound",)),
    ("AL-PKG-002", "component_atopology.c", ("atopology", "asound")),
)

REQUIRED_COMPONENTS = {
    "mixer",
    "pcm",
    "rawmidi",
    "hwdep",
    "seq",
    "ucm",
    "topology",
}

REQUIRED_PCM_PLUGINS = {
    "copy",
    "linear",
    "route",
    "plug",
    "file",
    "null",
    "empty",
    "asym",
    "iec958",
    "softvol",
}


class AlsaLibTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "*.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        CMakeDeps(self).generate()
        PkgConfigDeps(self).generate()

        temp_dir = Path(self.build_folder, ".tmp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temp_dir))
        environment.vars(self).save_script("alsa_test_env")

        relocated = Path(self.build_folder, "relocated-package")
        relocated_environment = Environment()
        relocated_environment.define_path(
            "ALSA_CONFIG_DIR", str(relocated / "share" / "alsa")
        )
        relocated_environment.define_path(
            "ALSA_CONFIG_PATH", str(relocated / "share" / "alsa" / "alsa.conf")
        )
        relocated_environment.define_path(
            "ALSA_PLUGIN_DIR", str(relocated / "lib" / "alsa-lib")
        )
        relocated_environment.prepend_path(
            "LD_LIBRARY_PATH", str(relocated / "lib")
        )
        relocated_environment.vars(self).save_script("alsa_relocated_env")

    def build(self):
        self._validate_case_registry()

        tested = self.dependencies[self.tested_reference_str]
        package = Path(tested.package_folder)
        compiler = self._c_compiler()
        linkage = self._system_linkage(tested)
        self._validate_conan_generator_contract(package)
        shared_definitions = (
            ("-DCHECK_DSO_PATH=1",) if self._is_shared(tested) else ()
        )
        failures = []

        for identifier, symbol, header in ABI_PROBES:
            self._attempt_build(
                identifier,
                lambda identifier=identifier, symbol=symbol, header=header:
                self._compile(
                    compiler,
                    Path(self.source_folder, "api_probe.c"),
                    self._executable(identifier),
                    package / "include",
                    package / "lib",
                    ("atopology", "asound")
                    if symbol == "snd_tplg_new" else ("asound",),
                    linkage,
                    (
                        f"-DAPI_HEADER=<{header}>",
                        f"-DAPI_SYMBOL={symbol}",
                    ),
                ),
                failures,
            )

        for identifier, source_name, libraries in (
            *BEHAVIOR_CASES,
            *COMPONENT_CASES,
        ):
            definitions = (
                shared_definitions if identifier.startswith("AL-PKG-") else ()
            )
            self._attempt_build(
                identifier,
                lambda identifier=identifier, source_name=source_name,
                libraries=libraries, definitions=definitions: self._compile(
                    compiler,
                    Path(self.source_folder, source_name),
                    self._executable(identifier),
                    package / "include",
                    package / "lib",
                    libraries,
                    linkage,
                    definitions,
                ),
                failures,
            )

        self._attempt_build(
            "AL-PKG-005-env",
            lambda: self._compile(
                compiler,
                Path(self.source_folder, "feature_contract.c"),
                self._executable("AL-PKG-005-env"),
                package / "include",
                package / "lib",
                ("asound",),
                linkage,
            ),
            failures,
        )

        if not self._is_shared(tested):
            self._attempt_build(
                "AL-PKG-004-static-pic",
                lambda: self._compile_static_pic_probe(
                    compiler,
                    package,
                    linkage,
                ),
                failures,
            )

        relocated = Path(self.build_folder, "relocated-package")
        self._attempt_build(
            "AL-PKG-003-copy",
            lambda: self._prepare_relocated_package(package, relocated),
            failures,
        )
        if relocated.is_dir():
            self._attempt_build(
                "AL-PKG-003-pc",
                lambda: self._validate_pkg_config(relocated, package),
                failures,
            )
            for suffix, source_name, libraries in (
                ("asound", "component_asound.c", ("asound",)),
                ("atopology", "component_atopology.c", ("atopology", "asound")),
            ):
                self._attempt_build(
                    f"AL-PKG-003-{suffix}",
                    lambda suffix=suffix, source_name=source_name,
                    libraries=libraries: self._compile(
                        compiler,
                        Path(self.source_folder, source_name),
                        self._executable(f"AL-PKG-003-{suffix}"),
                        relocated / "include",
                        relocated / "lib",
                        libraries,
                        linkage,
                        shared_definitions,
                    ),
                    failures,
                )

        if failures:
            details = "\n".join(f"- {failure}" for failure in failures)
            raise ConanException(
                f"{len(failures)} ALSA consumer/probe builds failed:\n{details}"
            )

    def test(self):
        if cross_building(self) or not can_run(self):
            self.output.info(
                "NOT_RUN ALSA_TARGET_ENTRIES=11 reason=cross_building"
            )
            return

        tested = self.dependencies[self.tested_reference_str]
        package = Path(tested.package_folder)
        relocated = Path(self.build_folder, "relocated-package")
        shared = self._is_shared(tested)
        package_marker = str(package) if shared else "-"
        relocated_marker = str(relocated) if shared else "-"
        failures = []
        self._start_consumer_signing_evidence()

        cases = []
        for identifier, _source_name, _libraries in BEHAVIOR_CASES:
            cases.append(
                (
                    identifier,
                    lambda identifier=identifier: self._execute(
                        self._executable(identifier),
                        (),
                        ("conanrun", "alsa_test_env"),
                    ),
                    identifier,
                )
            )
        for identifier, _source_name, _libraries in COMPONENT_CASES:
            cases.append(
                (
                    identifier,
                    lambda identifier=identifier: self._execute(
                        self._executable(identifier),
                        ("1.2.16.1", package_marker),
                        ("conanrun", "alsa_test_env"),
                    ),
                    identifier,
                )
            )

        cases.extend(
            (
                (
                    "AL-PKG-003",
                    lambda: self._test_relocated_package(
                        relocated, relocated_marker
                    ),
                    "relocated pkg-config and runtime consumers",
                ),
                (
                    "AL-PKG-004",
                    lambda: self._validate_artifact_set(package, shared),
                    "artifact and ABI contract",
                ),
                (
                    "AL-PKG-005",
                    lambda: self._test_feature_contract(package),
                    "feature and runtime metadata contract",
                ),
            )
        )

        for identifier, callback, detail in cases:
            try:
                callback()
            except Exception as error:  # Conan converts the aggregate to one failure.
                failures.append(f"{identifier}:{detail}: {error}")
            else:
                self.output.info(f"PASS {identifier}:{detail}")

        try:
            self._validate_consumer_signing_evidence()
        except Exception as error:
            failures.append(f"AL-SIGNING:consumer signing evidence: {error}")

        if failures:
            details = "\n".join(f"- {failure}" for failure in failures)
            raise ConanException(
                f"{len(failures)} of 11 ALSA test-package entries failed:\n"
                f"{details}"
            )
        self.output.info("validated 11 independent ALSA test-package entries")

    def _validate_case_registry(self):
        probe_identifiers = [case[0] for case in ABI_PROBES]
        test_identifiers = [case[0] for case in BEHAVIOR_CASES]
        test_identifiers.extend(case[0] for case in COMPONENT_CASES)
        test_identifiers.extend(("AL-PKG-003", "AL-PKG-004", "AL-PKG-005"))
        symbols = [case[1] for case in ABI_PROBES]
        if (
            len(ABI_PROBES) != 60
            or len(BEHAVIOR_CASES) != 6
            or len(COMPONENT_CASES) != 2
            or len(probe_identifiers) != 60
            or len(set(probe_identifiers)) != 60
            or len(test_identifiers) != 11
            or len(set(test_identifiers)) != 11
            or set(probe_identifiers) & set(test_identifiers)
            or len(set(symbols)) != 60
        ):
            raise ConanException(
                "expected 60 unique ABI probes and 11 unique test entries"
            )

    def _attempt_build(self, identifier, callback, failures):
        try:
            callback()
        except Exception as error:
            failures.append(f"{identifier}: {error}")

    def _compile(
        self,
        compiler,
        source,
        executable,
        include_dir,
        lib_dir,
        libraries,
        system_linkage,
        definitions=(),
    ):
        command = [
            compiler,
            "-std=gnu11",
            "-Wall",
            "-Wextra",
            "-Werror",
            *definitions,
            f"-I{include_dir}",
            str(source),
            "-o",
            str(executable),
            f"-L{lib_dir}",
            *(f"-l{name}" for name in libraries),
            *system_linkage,
        ]
        self._run_entry(command, ("conanbuild", "alsa_test_env"))

    def _compile_static_pic_probe(self, compiler, package, system_linkage):
        output = Path(self.build_folder, "al-pkg-004-static-pic.so")
        if output.exists():
            output.unlink()
        command = [
            compiler,
            "-std=gnu11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-fPIC",
            "-shared",
            "-Wl,-z,defs",
            f"-I{Path(package, 'include')}",
            str(Path(self.source_folder, "component_asound.c")),
            "-Wl,--whole-archive",
            str(Path(package, "lib", "libatopology.a")),
            str(Path(package, "lib", "libasound.a")),
            "-Wl,--no-whole-archive",
            "-o",
            str(output),
            *system_linkage,
        ]
        self._run_entry(command, ("conanbuild", "alsa_test_env"))

    def _execute(self, executable, arguments, environments):
        if not executable.is_file() or executable.stat().st_size == 0:
            raise ConanException(f"missing ALSA consumer: {executable.name}")
        self._sign_elf_for_ohos(executable)
        self._run_entry(
            [str(executable), *map(str, arguments)],
            environments,
        )

    def _run_entry(self, command, environments):
        if str(self.settings.os) == "OHOS":
            timeout = "/system/bin/timeout"
        else:
            timeout = shutil.which("timeout")
        if not timeout or not Path(timeout).is_file():
            raise ConanInvalidConfiguration(
                "an external timeout command is required for every test entry"
            )
        self.run(
            shlex.join([str(timeout), "180", *map(str, command)]),
            env=list(environments),
        )

    def _test_relocated_package(self, relocated, package_marker):
        self._validate_pkg_config(relocated)
        environments = ("conanrun", "alsa_test_env", "alsa_relocated_env")
        self._execute(
            self._executable("AL-PKG-003-asound"),
            ("1.2.16.1", package_marker),
            environments,
        )
        self._execute(
            self._executable("AL-PKG-003-atopology"),
            ("1.2.16.1", package_marker),
            environments,
        )

    def _prepare_relocated_package(self, package, relocated):
        if relocated.exists():
            shutil.rmtree(relocated)
        shutil.copytree(package, relocated, symlinks=True)

    def _validate_pkg_config(self, package, original_package=None):
        metadata = {
            name: self._read_pkg_config(
                package / "lib" / "pkgconfig" / f"{name}.pc"
            )
            for name in ("alsa", "alsa-topology")
        }
        expected_root = package.resolve()
        for name, values in metadata.items():
            if values["fields"].get("Version") != "1.2.16.1":
                raise ConanException(f"{name}.pc has the wrong Version")
            prefix = Path(values["variables"]["prefix"]).resolve()
            if prefix != expected_root:
                raise ConanException(
                    f"{name}.pc resolves prefix outside the package: {prefix}"
                )
            if original_package is not None and str(original_package) in values["text"]:
                raise ConanException(f"{name}.pc leaks the original package path")

        alsa = metadata["alsa"]
        include_paths = {
            Path(token[2:]).resolve()
            for token in shlex.split(alsa["fields"]["Cflags"])
            if token.startswith("-I") and len(token) > 2
        }
        library_paths = {
            Path(token[2:]).resolve()
            for token in shlex.split(alsa["fields"]["Libs"])
            if token.startswith("-L") and len(token) > 2
        }
        if expected_root / "include" not in include_paths:
            raise ConanException("alsa.pc does not resolve the relocated include path")
        alsa_libs = shlex.split(alsa["fields"]["Libs"])
        if expected_root / "lib" not in library_paths or "-lasound" not in alsa_libs:
            raise ConanException("alsa.pc does not resolve the relocated library")

        topology = metadata["alsa-topology"]
        if "-latopology" not in shlex.split(topology["fields"]["Libs"]):
            raise ConanException("alsa-topology.pc does not expose libatopology")
        if not topology["fields"].get("Requires", "").startswith(
            "alsa >= 1.2.16.1"
        ):
            raise ConanException("alsa-topology.pc lost its libasound dependency")

    def _read_pkg_config(self, path):
        if not path.is_file():
            raise ConanException(f"missing pkg-config file: {path.name}")
        text = path.read_text(encoding="utf-8")
        variables = {"pcfiledir": str(path.parent)}
        fields = {}
        for line in text.splitlines():
            variable = re.match(r"^([A-Za-z][A-Za-z0-9_]*)=(.*)$", line)
            if variable:
                variables[variable.group(1)] = variable.group(2).strip()
                continue
            field = re.match(r"^([A-Za-z][A-Za-z0-9.]*):\s*(.*)$", line)
            if field:
                fields[field.group(1)] = field.group(2).strip()

        for _iteration in range(12):
            changed = False
            for key, value in tuple(variables.items()):
                expanded = re.sub(
                    r"\$\{([^}]+)\}",
                    lambda match: variables.get(match.group(1), match.group(0)),
                    value,
                )
                if expanded != value:
                    variables[key] = expanded
                    changed = True
            if not changed:
                break
        if any("${" in value for value in variables.values()):
            raise ConanException(f"unresolved variable in {path.name}")
        fields = {
            key: re.sub(
                r"\$\{([^}]+)\}",
                lambda match: variables.get(match.group(1), match.group(0)),
                value,
            )
            for key, value in fields.items()
        }
        if any("${" in value for value in fields.values()):
            raise ConanException(f"unresolved field in {path.name}")
        return {"text": text, "variables": variables, "fields": fields}

    def _validate_artifact_set(self, package, shared):
        self._validate_signing_manifest(package, shared)
        headers = sorted(
            path.relative_to(package).as_posix()
            for path in (package / "include").rglob("*.h")
        )
        if len(headers) != 50 or len(set(headers)) != 50:
            raise ConanException(
                f"expected 50 unique installed headers, found {len(headers)}"
            )

        configs = sorted(
            path.relative_to(package).as_posix()
            for path in (package / "share" / "alsa").rglob("*.conf")
        )
        if len(configs) != 78 or len(set(configs)) != 78:
            raise ConanException(
                f"expected 78 unique ALSA configuration files, found {len(configs)}"
            )

        pc_names = sorted(
            path.name for path in (package / "lib" / "pkgconfig").glob("*.pc")
        )
        if pc_names != ["alsa-topology.pc", "alsa.pc"]:
            raise ConanException(f"unexpected pkg-config files: {pc_names}")
        if not Path(package, "licenses", "COPYING").is_file():
            raise ConanException("COPYING was not packaged")
        if not Path(
            package, "share", "alsa", "conan-feature-contract.json"
        ).is_file():
            raise ConanException("feature contract was not packaged")

        if shared:
            for stem in ("asound", "atopology"):
                self._validate_shared_family(package, stem)
            self._require_needed(
                self._executable("AL-PKG-001"),
                self._shared_soname("asound"),
            )
            self._require_needed(
                self._executable("AL-PKG-002"),
                self._shared_soname("atopology"),
            )
            self._require_needed(
                Path(package, "lib", "libatopology.so"),
                self._shared_soname("asound"),
            )
        else:
            for stem in ("asound", "atopology"):
                archive = Path(package, "lib", f"lib{stem}.a")
                if not archive.is_file() or archive.stat().st_size == 0:
                    raise ConanException(f"missing static library: {archive.name}")
                if list(Path(package, "lib").glob(f"lib{stem}.so*")):
                    raise ConanException(f"static package contains lib{stem}.so files")
            self._validate_static_pic_probe()
            self._reject_needed(self._executable("AL-PKG-001"), "libasound.so")
            self._reject_needed(self._executable("AL-PKG-002"), "libatopology.so")

    def _validate_static_pic_probe(self):
        output = Path(self.build_folder, "al-pkg-004-static-pic.so")
        if not self._is_elf(output):
            raise ConanException("static libasound PIC probe did not produce an ELF")
        header = self._readelf("-h", output)
        if not re.search(r"^\s*Type:\s+DYN\b", header, re.MULTILINE):
            raise ConanException("static PIC probe is not a shared ELF")
        self._reject_needed(output, "libasound.so")
        self._reject_needed(output, "libatopology.so")
        dynamic = self._readelf("-d", output)
        if re.search(r"\((?:RPATH|RUNPATH)\)", dynamic):
            raise ConanException("static PIC probe contains a runtime search path")

    def _validate_shared_family(self, package, stem):
        platform = str(self.settings.os)
        if platform == "OHOS":
            self._validate_ohos_shared_family(package, stem)
        elif platform == "Linux":
            self._validate_linux_shared_family(package, stem)
        else:
            raise ConanException(f"unsupported shared-library platform: {platform}")

    def _validate_ohos_shared_family(self, package, stem):
        library_dir = Path(package, "lib")
        linker_name = library_dir / f"lib{stem}.so"
        family = sorted(library_dir.glob(f"lib{stem}.so*"))
        if family != [linker_name]:
            raise ConanException(
                f"lib{stem} must have one unversioned shared object: "
                f"{[path.name for path in family]}"
            )
        if linker_name.is_symlink() or linker_name.stat().st_size == 0:
            raise ConanException(f"lib{stem}.so is not one real shared object")
        with linker_name.open("rb") as stream:
            if stream.read(4) != b"\x7fELF":
                raise ConanException(f"lib{stem}.so is not an ELF")

        dynamic = self._readelf("-d", linker_name)
        sonames = re.findall(r"\(SONAME\).*\[([^]]+)\]", dynamic)
        expected = f"lib{stem}.so"
        if sonames != [expected]:
            raise ConanException(
                f"{linker_name.name} SONAME is {sonames}, not {expected}"
            )

    def _validate_linux_shared_family(self, package, stem):
        library_dir = Path(package, "lib")
        linker_name = library_dir / f"lib{stem}.so"
        soname_path = library_dir / f"lib{stem}.so.2"
        real_library = library_dir / f"lib{stem}.so.2.0.0"
        expected_family = [linker_name, soname_path, real_library]
        family = sorted(library_dir.glob(f"lib{stem}.so*"))
        if family != expected_family:
            raise ConanException(
                f"lib{stem} Linux shared family is "
                f"{[path.name for path in family]}, expected "
                f"{[path.name for path in expected_family]}"
            )
        if real_library.is_symlink() or real_library.stat().st_size == 0:
            raise ConanException(
                f"{real_library.name} is not one real versioned shared object"
            )
        expected_sha = self._sha256(real_library)
        for path in expected_family:
            if not path.is_file() or self._sha256(path) != expected_sha:
                raise ConanException(
                    f"Linux shared alias does not resolve to {real_library.name}: "
                    f"{path.name}"
                )
            with path.open("rb") as stream:
                if stream.read(4) != b"\x7fELF":
                    raise ConanException(f"{path.name} is not an ELF")

        dynamic = self._readelf("-d", real_library)
        sonames = re.findall(r"\(SONAME\).*\[([^]]+)\]", dynamic)
        if sonames != [soname_path.name]:
            raise ConanException(
                f"{real_library.name} SONAME is {sonames}, not {soname_path.name}"
            )

    def _shared_soname(self, stem):
        suffix = "" if str(self.settings.os) == "OHOS" else ".2"
        return f"lib{stem}.so{suffix}"

    def _test_feature_contract(self, package):
        contract_path = Path(
            package, "share", "alsa", "conan-feature-contract.json"
        )
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        if contract.get("schema") != 1 or contract.get("version") != "1.2.16.1":
            raise ConanException("feature contract schema/version mismatch")

        components = contract.get("components", {})
        missing_components = sorted(
            name for name in REQUIRED_COMPONENTS if components.get(name) is not True
        )
        if missing_components:
            raise ConanException(
                f"required components are disabled: {missing_components}"
            )
        plugins = set(contract.get("pcm_plugins", ()))
        missing_plugins = sorted(REQUIRED_PCM_PLUGINS - plugins)
        if missing_plugins:
            raise ConanException(f"required PCM plug-ins are disabled: {missing_plugins}")

        topology_present = any(
            Path(package, "lib").glob("libatopology.*")
        )
        if bool(components.get("topology")) != topology_present:
            raise ConanException("topology feature metadata does not match artifacts")
        aserver_present = Path(package, "bin", "aserver").is_file()
        if contract.get("aserver") is not aserver_present:
            raise ConanException("aserver feature metadata does not match artifacts")
        if contract.get("commands_required") is not aserver_present:
            raise ConanException("aserver command metadata requirement is inconsistent")

        compiled_paths = contract.get("compiled_paths", {})
        path_policy = contract.get("path_policy", {})
        for name in (
            "ALSA_CONFIG_DIR",
            "ALSA_PLUGIN_DIR",
            "ALSA_DEVICE_DIRECTORY",
            "TMPDIR",
        ):
            value = compiled_paths.get(name)
            if not isinstance(value, str) or not value.startswith("/"):
                raise ConanException(f"invalid compiled path for {name}: {value}")
            if str(package) in value or str(self.build_folder) in value:
                raise ConanException(f"compiled path leaks a build/package folder: {name}")
            if not isinstance(path_policy.get(name), str) or not path_policy[name]:
                raise ConanException(f"compiled path lacks an explicit policy: {name}")

        config_dir = Path(package, "share", "alsa")
        config_path = config_dir / "alsa.conf"
        plugin_dir = Path(package, "lib", "alsa-lib")
        temp_dir = Path(self.build_folder, ".tmp")
        self._execute(
            self._executable("AL-PKG-005-env"),
            (config_dir, config_path, plugin_dir, temp_dir),
            ("conanrun", "alsa_test_env"),
        )

    def _require_needed(self, path, expected):
        dynamic = self._readelf("-d", path)
        needed = re.findall(r"\(NEEDED\).*\[([^]]+)\]", dynamic)
        if expected not in needed:
            raise ConanException(f"{path.name} NEEDED lacks {expected}: {needed}")

    def _reject_needed(self, path, forbidden_prefix):
        dynamic = self._readelf("-d", path)
        needed = re.findall(r"\(NEEDED\).*\[([^]]+)\]", dynamic)
        if any(name.startswith(forbidden_prefix) for name in needed):
            raise ConanException(f"{path.name} unexpectedly needs {forbidden_prefix}")

    def _readelf(self, option, path):
        if not path.is_file():
            raise ConanException(f"ELF input is missing: {path}")
        tool = self._readelf_tool()
        completed = subprocess.run(
            [tool, option, str(path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if completed.returncode != 0:
            raise ConanException(
                f"{Path(tool).name} failed for {path.name}: {completed.stdout}"
            )
        return completed.stdout

    def _readelf_tool(self):
        compiler = Path(self._c_compiler())
        candidates = (
            compiler.with_name("llvm-readelf"),
            shutil.which("llvm-readelf"),
            shutil.which("readelf"),
        )
        for candidate in candidates:
            if candidate and Path(candidate).is_file():
                return str(candidate)
        raise ConanInvalidConfiguration("llvm-readelf or readelf is required")

    def _system_linkage(self, tested):
        asound = tested.cpp_info.components["asound"]
        return [
            *(f"-l{name}" for name in asound.system_libs),
            *asound.exelinkflags,
        ]

    def _is_shared(self, tested):
        value = tested.options.get_safe("shared")
        return str(value).lower() == "true"

    def _executable(self, identifier):
        return Path(self.build_folder, identifier.lower())

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

    def _validate_conan_generator_contract(self, package):
        generators = Path(self.generators_folder)
        cmake_files = sorted(generators.glob("*.cmake"))
        cmake_text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in cmake_files
        )
        missing_targets = [
            target
            for target in ("ALSA::ALSA", "ALSA::asound", "ALSA::atopology")
            if target not in cmake_text
        ]
        if not cmake_files or missing_targets:
            raise ConanException(
                f"CMakeDeps contract is incomplete: {missing_targets}"
            )

        pc_files = sorted(generators.glob("*.pc"))
        pc_metadata = [self._read_pkg_config(path) for path in pc_files]
        pc_tokens = {
            token
            for metadata in pc_metadata
            for field in ("Cflags", "Libs", "Libs.private")
            for token in shlex.split(metadata["fields"].get(field, ""))
        }
        required_pc_tokens = (
            "-lasound",
            "-latopology",
            f"-I{package / 'include'}",
            f"-L{package / 'lib'}",
        )
        missing_pc_tokens = [
            token for token in required_pc_tokens if token not in pc_tokens
        ]
        if not pc_files or missing_pc_tokens:
            raise ConanException(
                f"PkgConfigDeps contract is incomplete: {missing_pc_tokens}"
            )

    def _validate_signing_manifest(self, package, shared):
        if str(self.settings.os) != "OHOS":
            return
        manifest_path = Path(
            package,
            "share",
            "alsa",
            "conan-elf-signatures.json",
        )
        if not manifest_path.is_file():
            raise ConanException("package ELF signing manifest is missing")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_paths = {"bin/aserver"}
        if shared:
            expected_paths.update(("lib/libasound.so", "lib/libatopology.so"))
        expected_mode = "shared" if shared else "static"
        if (
            manifest.get("schema") != 1
            or manifest.get("package_mode") != expected_mode
            or not isinstance(manifest.get("entries"), list)
        ):
            raise ConanException("package ELF signing manifest header is invalid")

        entries = manifest["entries"]
        paths = [entry.get("path") for entry in entries]
        if len(paths) != len(set(paths)) or set(paths) != expected_paths:
            raise ConanException(f"package signing paths are invalid: {paths}")
        actual_elfs = {
            path.relative_to(package).as_posix()
            for path in Path(package).rglob("*")
            if path.is_file() and self._is_elf(path)
        }
        if actual_elfs != expected_paths:
            raise ConanException(
                f"package ELF set is {sorted(actual_elfs)}, "
                f"expected {sorted(expected_paths)}"
            )

        hex_digest = re.compile(r"[0-9a-f]{64}")
        tools = self._require_sign_tools()
        for entry in entries:
            if set(entry) != {
                "path",
                "before_sha256",
                "after_sha256",
                "codesign_size",
                "codesign_sha256",
            }:
                raise ConanException("package signing entry fields are invalid")
            relative = entry["path"]
            path = Path(package, *relative.split("/"))
            if path.is_symlink() or not self._is_elf(path):
                raise ConanException(f"invalid signed package ELF: {relative}")
            metadata = self._codesign_metadata(path, tools)
            if (
                not hex_digest.fullmatch(entry["before_sha256"])
                or self._sha256(path) != entry["after_sha256"]
                or metadata["size"] != entry["codesign_size"]
                or metadata["sha256"] != entry["codesign_sha256"]
            ):
                raise ConanException(
                    f"package signing evidence mismatch for {relative}"
                )

    def _start_consumer_signing_evidence(self):
        self._consumer_signed_paths = set()
        evidence = Path(self.build_folder, "consumer-elf-signatures.tsv")
        evidence.write_text("", encoding="utf-8")

    def _validate_consumer_signing_evidence(self):
        if str(self.settings.os) != "OHOS":
            return
        expected_identifiers = {
            *(case[0] for case in BEHAVIOR_CASES),
            *(case[0] for case in COMPONENT_CASES),
            "AL-PKG-003-asound",
            "AL-PKG-003-atopology",
            "AL-PKG-005-env",
        }
        expected_paths = {
            self._executable(identifier)
            .relative_to(self.build_folder)
            .as_posix()
            for identifier in expected_identifiers
        }
        evidence = Path(self.build_folder, "consumer-elf-signatures.tsv")
        rows = []
        for index, line in enumerate(
            evidence.read_text(encoding="utf-8").splitlines(), start=1
        ):
            fields = line.split("\t")
            if len(fields) != 5 or any(not field for field in fields):
                raise ConanException(f"invalid consumer signing row {index}")
            rows.append(fields)
        paths = [row[0] for row in rows]
        if len(rows) != 11 or len(paths) != len(set(paths)):
            raise ConanException("consumer ELFs were not signed exactly once")
        if set(paths) != expected_paths:
            raise ConanException(
                f"consumer signing paths are {sorted(paths)}, "
                f"expected {sorted(expected_paths)}"
            )

        hex_digest = re.compile(r"[0-9a-f]{64}")
        tools = self._require_sign_tools()
        for relative, before_sha, after_sha, codesign_size, codesign_sha in rows:
            path = Path(self.build_folder, *relative.split("/"))
            metadata = self._codesign_metadata(path, tools)
            if (
                not hex_digest.fullmatch(before_sha)
                or not hex_digest.fullmatch(after_sha)
                or not hex_digest.fullmatch(codesign_sha)
                or self._sha256(path) != after_sha
                or metadata["size"] != int(codesign_size)
                or metadata["sha256"] != codesign_sha
            ):
                raise ConanException(
                    f"consumer signing evidence mismatch for {relative}"
                )

    def _sign_elf_for_ohos(self, path):
        if str(self.settings.os) != "OHOS":
            return
        path = Path(path)
        relative = path.relative_to(self.build_folder).as_posix()
        if relative in self._consumer_signed_paths:
            raise ConanException(f"consumer ELF would be signed twice: {relative}")
        entry = self._sign_elf(path, self._require_sign_tools())
        with Path(
            self.build_folder, "consumer-elf-signatures.tsv"
        ).open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(
                "\t".join(
                    (
                        relative,
                        entry["before_sha256"],
                        entry["after_sha256"],
                        str(entry["codesign_size"]),
                        entry["codesign_sha256"],
                    )
                )
                + "\n"
            )
        self._consumer_signed_paths.add(relative)

    def _sign_elf(self, path, tools):
        if not path.is_file() or path.is_symlink() or not self._is_elf(path):
            raise ConanException(f"invalid consumer ELF signing input: {path}")
        before_sha = self._sha256(path)
        mode = path.stat().st_mode & 0o7777
        clean = Path(f"{path}.alsa-codesign-clean-{os.getpid()}")
        signed = Path(f"{path}.alsa-codesign-signed-{os.getpid()}")
        for temporary in (clean, signed):
            if os.path.lexists(temporary):
                temporary.unlink()
        try:
            self._run_subprocess(
                [
                    tools["objcopy"],
                    "--remove-section",
                    ".codesign",
                    str(path),
                    str(clean),
                ],
                f"remove old .codesign from {path.name}",
            )
            if not self._is_elf(clean):
                raise ConanException(f"ELF cleanup produced invalid output: {path}")
            if self._codesign_count(clean, tools["readelf"]) != 0:
                raise ConanException(f"ELF cleanup retained .codesign: {path}")
            self._run_subprocess(
                [
                    tools["signer"],
                    "sign",
                    "-inFile",
                    str(clean),
                    "-outFile",
                    str(signed),
                    "-selfSign",
                    "1",
                ],
                f"sign {path.name}",
            )
            if not self._is_elf(signed):
                raise ConanException(f"ELF signer produced invalid output: {path}")
            metadata = self._codesign_metadata(signed, tools)
            os.chmod(signed, mode)
            after_sha = self._sha256(signed)
            path.unlink()
            os.replace(signed, path)
        finally:
            for temporary in (clean, signed):
                if os.path.lexists(temporary):
                    temporary.unlink()
        return {
            "before_sha256": before_sha,
            "after_sha256": after_sha,
            "codesign_size": metadata["size"],
            "codesign_sha256": metadata["sha256"],
        }

    def _codesign_metadata(self, path, tools):
        count = self._codesign_count(path, tools["readelf"])
        if count != 1:
            raise ConanException(
                f"{path.name} has {count} .codesign sections, expected one"
            )
        dump = Path(f"{path}.alsa-codesign-dump-{os.getpid()}")
        inspect = Path(f"{path}.alsa-codesign-inspect-{os.getpid()}")
        for temporary in (dump, inspect):
            if os.path.lexists(temporary):
                temporary.unlink()
        try:
            shutil.copy2(path, inspect)
            self._run_subprocess(
                [
                    tools["objcopy"],
                    "--dump-section",
                    f".codesign={dump}",
                    str(inspect),
                ],
                f"dump .codesign from {path.name}",
            )
            if not dump.is_file() or dump.stat().st_size <= 0:
                raise ConanException(f"{path.name} has an empty .codesign section")
            return {
                "size": dump.stat().st_size,
                "sha256": self._sha256(dump),
            }
        finally:
            for temporary in (dump, inspect):
                if os.path.lexists(temporary):
                    temporary.unlink()

    def _codesign_count(self, path, readelf):
        completed = self._run_subprocess(
            [readelf, "-SW", str(path)],
            f"inspect sections for {path.name}",
        )
        return sum(
            1
            for line in completed.stdout.splitlines()
            if ".codesign" in line.split()
        )

    @staticmethod
    def _require_sign_tools():
        tools = {
            "objcopy": "/data/service/hnp/bin/llvm-objcopy",
            "readelf": "/data/service/hnp/bin/llvm-readelf",
            "signer": "/data/service/hnp/bin/binary-sign-tool",
        }
        missing = [path for path in tools.values() if not os.path.isfile(path)]
        if missing:
            raise ConanInvalidConfiguration(
                f"HarmonyOS ELF signing tools are required: {missing}"
            )
        return tools

    @staticmethod
    def _run_subprocess(command, purpose):
        try:
            completed = subprocess.run(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ConanException(f"{purpose} failed: {error}") from error
        if completed.returncode != 0:
            detail = completed.stdout.strip()[-500:]
            raise ConanException(
                f"{purpose} failed with rc={completed.returncode}: {detail}"
            )
        return completed

    @staticmethod
    def _sha256(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @staticmethod
    def _is_elf(path):
        try:
            with Path(path).open("rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False
