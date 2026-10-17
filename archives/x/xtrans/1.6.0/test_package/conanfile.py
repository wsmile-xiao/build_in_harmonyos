#!/usr/bin/env python3
"""Conan consumer matrix for xtrans 1.6.0."""

import hashlib
import os
import sys
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


NAMESPACE_CASES = (
    ("default", ()),
    ("x11", ("X11_t",)),
    ("xim", ("XIM_t",)),
    ("fs", ("FS_t",)),
    ("font", ("FONT_t",)),
    ("ice", ("ICE_t",)),
)
ROLE_CASES = (
    ("client", ("TRANS_CLIENT",)),
    ("server", ("TRANS_SERVER",)),
    ("server_reopen", ("TRANS_SERVER", "TRANS_REOPEN")),
    ("full", ("TRANS_CLIENT", "TRANS_SERVER", "TRANS_REOPEN")),
)
TRANSPORT_CASES = (
    ("tcp", ("TCPCONN",)),
    ("tcp_ipv6", ("TCPCONN", "IPv6")),
    ("unix", ("UNIXCONN", "XTRANS_SEND_FDS=1")),
)
EXPECTED_CASE_COUNT = 68
EXPECTED_SUBSTANTIVE_TEST_COUNT = 4
RUNTIME_HASH_LENGTH = 16
RUNTIME_PORT_BUFFER_SIZE = 80
UNIX_SOCKET_PATH_LIMIT = 108
MAX_PID_DIGITS = 10
MAX_ENDPOINT_ATTEMPT = 63


class XtransTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = (
        "configure_probe.c",
        "consumer.c",
        "runtime_smoke.c",
        "verify_package.py",
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        temp_dir = Path(self.build_folder, ".tmp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        runtime_dir = self._runtime_dir()
        longest_endpoint = runtime_dir / (
            f"xtrans-{'9' * MAX_PID_DIGITS}-{MAX_ENDPOINT_ATTEMPT}"
        )
        endpoint_length = len(os.fsencode(longest_endpoint))
        if endpoint_length >= RUNTIME_PORT_BUFFER_SIZE:
            raise ConanException(
                "xtrans runtime endpoint exceeds the C port buffer: "
                f"{endpoint_length} >= {RUNTIME_PORT_BUFFER_SIZE}"
            )
        if endpoint_length >= UNIX_SOCKET_PATH_LIMIT:
            raise ConanException(
                "xtrans runtime endpoint exceeds the UNIX socket path limit: "
                f"{endpoint_length} >= {UNIX_SOCKET_PATH_LIMIT}"
            )
        runtime_dir.parent.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temp_dir))
        environment.define_path("XTRANS_TEST_RUNTIME_DIR", str(runtime_dir))
        environment.vars(self).save_script("xtrans_test_env")

    def build(self):
        compiler = self._c_compiler()
        include_dirs = []
        for _name, dependency in self.dependencies.items():
            include_dirs.extend(dependency.cpp_info.includedirs)
        include_flags = " ".join(f'-I"{path}"' for path in include_dirs)

        tested = self.dependencies[self.tested_reference_str]
        package_defines = tuple(tested.cpp_info.defines)
        package_define_flags = " ".join(
            f"-D{define}" for define in package_defines
        )
        template = Path(self.source_folder, "consumer.c").read_text(
            encoding="utf-8"
        )
        build_dir = Path(self.build_folder)
        build_dir.mkdir(parents=True, exist_ok=True)

        configure_probe = Path(self.source_folder, "configure_probe.c")
        self.run(
            f'"{compiler}" -std=c11 -Werror -fsyntax-only '
            f'-D_DEFAULT_SOURCE -D_BSD_SOURCE "{configure_probe}"',
            env=["conanbuild", "xtrans_test_env"],
        )
        capability_flags = " ".join(
            f"-D{define}"
            for define in (
                "HAVE_SOCKLEN_T",
                "HAVE_STRUCT_SOCKADDR_STORAGE",
                "HAVE_GETADDRINFO",
                "HAVE_INET_NTOP",
            )
        )

        cases = self._cases()
        if len(cases) != EXPECTED_CASE_COUNT:
            raise ConanException(f"expected {EXPECTED_CASE_COUNT} xtrans cases")
        for case_id, macros in cases:
            source = build_dir / f"{case_id}.c"
            executable = build_dir / case_id
            source.write_text(
                template.replace("@XTRANS_CASE_ID@", case_id), encoding="utf-8"
            )
            case_flags = " ".join(f"-D{macro}" for macro in macros)
            self.run(
                f'"{compiler}" -std=c11 -Werror {include_flags} '
                f'{package_define_flags} {capability_flags} {case_flags} '
                f'"{source}" -o "{executable}"',
                env=["conanbuild", "xtrans_test_env"],
            )

        runtime_source = Path(self.source_folder, "runtime_smoke.c")
        for case_id, macros in self._runtime_cases():
            executable = build_dir / case_id
            case_flags = " ".join(f"-D{macro}" for macro in macros)
            self.run(
                f'"{compiler}" -std=c11 -Werror {include_flags} '
                f'{package_define_flags} {capability_flags} {case_flags} '
                f'"{runtime_source}" -o "{executable}"',
                env=["conanbuild", "xtrans_test_env"],
            )

    def test(self):
        build_dir = Path(self.build_folder)
        runtime_dir = self._runtime_dir()
        run_env = ["conanrun", "xtrans_test_env"]
        if runtime_dir.exists():
            raise ConanException(
                f"xtrans runtime directory already exists: {runtime_dir}"
            )
        runtime_dir.mkdir()
        try:
            cases = self._cases()
            for case_id, _macros in cases:
                executable = build_dir / case_id
                if not executable.is_file() or executable.stat().st_size == 0:
                    raise ConanException(f"missing xtrans consumer: {case_id}")

            runtime_cases = self._runtime_cases()
            for case_id, _macros in runtime_cases:
                executable = build_dir / case_id
                if not executable.is_file() or executable.stat().st_size == 0:
                    raise ConanException(
                        f"missing xtrans runtime smoke: {case_id}"
                    )
                self._run_case(f'"{executable}"', case_id, run_env)

            package_folder = self.dependencies[
                self.tested_reference_str
            ].package_folder
            verifier = Path(self.source_folder, "verify_package.py")
            self._run_case(
                f'"{sys.executable}" "{verifier}" "{package_folder}"',
                "package_metadata",
                run_env,
            )
        finally:
            self._remove_runtime_dir(runtime_dir)
        self.output.info(
            f"compiled {EXPECTED_CASE_COUNT} xtrans macro consumers as "
            "uncounted build preflights"
        )
        self.output.info(
            f"validated {EXPECTED_SUBSTANTIVE_TEST_COUNT} substantive tests: "
            "2 runtime transports, 1 OHOS UNIX capability workflow, and "
            "1 package contract"
        )

    def _remove_runtime_dir(self, runtime_dir):
        if not runtime_dir.is_dir():
            raise ConanException(
                f"missing xtrans runtime directory: {runtime_dir}"
            )
        residue = sorted(path.name for path in runtime_dir.iterdir())
        if residue:
            raise ConanException(f"xtrans runtime endpoint residue: {residue}")
        runtime_dir.rmdir()
        if runtime_dir.exists():
            raise ConanException(
                f"xtrans runtime directory was not removed: {runtime_dir}"
            )

    def _runtime_dir(self):
        build_folder = str(Path(self.build_folder).absolute())
        digest = hashlib.sha256(build_folder.encode("utf-8")).hexdigest()
        return Path.home() / "tmp" / f"xtr-{digest[:RUNTIME_HASH_LENGTH]}"

    def _run_case(self, command, case_id, run_env):
        self.run(command, env=run_env)
        self.output.info(f"XTRANS_TERMINAL\t{case_id}\tPASS")

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

    def _cases(self):
        cases = []
        for namespace_name, namespace_macros in NAMESPACE_CASES:
            for role_name, role_macros in ROLE_CASES:
                for transport_name, transport_macros in TRANSPORT_CASES:
                    if namespace_name == "default" and transport_name == "unix":
                        continue
                    case_id = f"{namespace_name}_{role_name}_{transport_name}"
                    macros = namespace_macros + role_macros + transport_macros
                    cases.append((case_id, macros))
        return cases

    def _runtime_cases(self):
        return (
            ("runtime_tcp4", ("XTRANS_TEST_TCP4",)),
            ("runtime_tcp6", ("XTRANS_TEST_TCP6", "IPv6")),
            ("runtime_local", ("XTRANS_TEST_LOCAL",)),
        )
