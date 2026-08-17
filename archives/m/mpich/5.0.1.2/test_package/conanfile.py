#!/usr/bin/env python3
"""Conan consumer and relocation tests for MPICH C and Fortran ABIs."""

import ast
import glob
import hashlib
import errno
import os
import re
import secrets
import signal
import shutil
import subprocess
import time
from contextlib import contextmanager, nullcontext
from shlex import quote, split

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    _flang_reference = "flang-ohos/20.1.0"
    _run_token_name = "MPICH_TEST_RUN_TOKEN"
    _llvm_license_sha256 = (
        "8d85c1057d742e597985c7d4e6320b015a9139385cff4cbae06ffc0ebe89afee"
    )
    _wrapper_names = (
        "mpicc",
        "mpicxx",
        "mpic++",
        "mpifort",
        "mpif77",
        "mpif90",
    )
    _launcher_names = ("mpiexec", "mpiexec.hydra", "mpirun", "hydra_pmi_proxy")
    _malformed_abort_probe_fragments = (
        '                      role, rank, (long) getpid(), process_group);\n',
        '    return write_file_once(path, marker);\n',
        'static int wait_for_observer_release(void)\n',
        '    static const char spawned_prefix[] = "--spawned=";\n',
        '    const char *argument;\n',
        '    } else if (argc == 1 &&\n'
        '               strncmp(argv[0], spawned_prefix, prefix_length) == 0) {\n',
        'static int build_spawned_argument(char *buffer, size_t capacity, const char *mode)\n',
        '        return "cmd=abort exitcode=1x message=trailing-junk\\n";\n',
        '        return "cmd=abort exitcode=2147483648 message=above-int\\n";\n',
        '        return "cmd=abort exitcode=-2147483649 message=below-int\\n";\n',
        '        return "cmd=abort exitcode=\\t1 message=leading-tab\\n";\n',
        '        return "cmd=abort exitcode=\\r1 message=leading-cr\\n";\n',
        '        return "cmd=abort exitcode=\\v1 message=leading-vt\\n";\n',
        '        return "cmd=abort exitcode=\\f1 message=leading-ff\\n";\n',
        '        return "cmd=abort exitcode=2147483647 message=valid-int-max\\n";\n',
        '        return "cmd=abort exitcode=-2147483648 message=valid-int-min\\n";\n',
        '    char spawned_argument[64];\n',
        '    /* MPI_Comm_spawn receives command separately; this payload contains '
        'arguments only. */\n',
        '    char *spawn_arguments[] = {spawned_argument, NULL};\n',
        '        if (wait_for_observer_release() != 0) {\n'
        '            return 155;\n'
        '        }\n'
        '        if (is_valid_mode(mode)) {\n',
        '            sleep(4);\n'
        '            if (write_canary_env("CODEX_MPI_VALID_CANARY", "spawned", 0) != 0) {\n'
        '                return 154;\n'
        '            }\n'
        '            sleep(120);\n',
        '        build_spawned_argument(spawned_argument, sizeof(spawned_argument), mode) != 0 ||\n',
        '        MPI_Comm_spawn(argv[0], spawn_arguments, 1, MPI_INFO_NULL, 0, '
        'MPI_COMM_WORLD,\n',
        '    if (wait_for_observer_release() != 0) {\n'
        '        return 159;\n'
        '    }\n',
        '        if (write_armed_marker(mode) != 0 ||\n',
        '        sleep(4);\n'
        '        if (write_canary_env("CODEX_MPI_VALID_CANARY", "parent", rank) != 0) {\n'
        '            return 160;\n'
        '        }\n'
        '        sleep(120);\n',
    )

    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = (
        "CMakeLists.txt",
        "MANIFEST.yml",
        "*.c",
        "*.cxx",
        "*.f",
        "*.f90",
    )

    _override_exact = {
        "BASH_ENV",
        "CDPATH",
        "CFLAGS",
        "CMAKE_FIND_PACKAGE_REDIRECTS_DIR",
        "CMAKE_FIND_ROOT_PATH",
        "CMAKE_MODULE_PATH",
        "CMAKE_PREFIX_PATH",
        "CMAKE_PROJECT_TOP_LEVEL_INCLUDES",
        "CMAKE_TOOLCHAIN_FILE",
        "COMPILER_PATH",
        "CPATH",
        "CPPFLAGS",
        "CPLUS_INCLUDE_PATH",
        "CXXFLAGS",
        "DEPENDENCIES_OUTPUT",
        "DYLD_INSERT_LIBRARIES",
        "ENV",
        "FCFLAGS",
        "FFLAGS",
        "GCC_EXEC_PREFIX",
        "HOME",
        "LD_AUDIT",
        "LDFLAGS",
        "LD_PRELOAD",
        "LIBRARY_PATH",
        "HYDRA_CONFIG_FILE",
        "HYDRA_ENV",
        "HYDRA_HOST_FILE",
        "HYDRA_IFACE",
        "HYDRA_USE_DDD",
        "HYDRA_USE_STRACE",
        "HYDRA_USE_VALGRIND",
        "MPICC",
        "MPICC_PROFILE",
        "MPICXX",
        "MPICXX_PROFILE",
        "MPIF77",
        "MPIF90",
        "MPIFC",
        "MPIFORT",
        "MPIFORT_PROFILE",
        "MPIR_CVAR_ALLREDUCE_INTRA_ALGORITHM",
        "MPIR_CVAR_PMI_VERSION",
        "MPIR_PARAM_CH3_PORT_RANGE",
        "MPICH_CC",
        "MPICH_CXX",
        "MPICH_FC",
        "MPICH_RECURSION_CHECK",
        "MPIEXEC",
        "MPIEXEC_PORT_RANGE",
        "MPIEXEC_PORTRANGE",
        "MPI_HOME",
        "MPI_ROOT",
        "PMIX_NAMESPACE",
        "PMI_SUBVERSION",
        "PMI_VERSION",
        "OBJC_INCLUDE_PATH",
        "PKG_CONFIG_LIBDIR",
        "PKG_CONFIG_PATH",
        "PKG_CONFIG_SYSROOT_DIR",
        "SUNPRO_DEPENDENCIES",
    }
    _override_pattern = re.compile(
        r"^(?:MPICH_|MPIR_(?:CVAR|PARAM)_|PMIX?_|HYDRA_|MPICC_|MPICXX_|MPIF77_|MPIF90_|MPIFC_|"
        r"MPIFORT_|MPIEXEC_)|_PROFILE$|_INCLUDE_PATH$"
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires(self._flang_reference, package_id_mode="full_mode")

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "mpich/5.0.1.2 tests require os=OHOS, arch=armv8"
            )

    def layout(self):
        basic_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.cache_variables["MPICH_FORTRAN_OBJECT"] = os.path.join(
            self.build_folder, "cmake_fortran_probe.o"
        )
        toolchain.generate()

    def _dep(self):
        return self.dependencies["mpich"]

    def _validate_license_contract(self, package_folder):
        license_dir = os.path.join(package_folder, "licenses")
        required = {
            "COPYRIGHT": None,
            "LLVM-LICENSE.TXT": self._llvm_license_sha256,
        }
        for name, expected_sha256 in required.items():
            path = os.path.join(license_dir, name)
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(
                    f"MPICH package is missing required license file: {name}"
                )
            if expected_sha256 is not None:
                with open(path, "rb") as stream:
                    actual_sha256 = hashlib.sha256(stream.read()).hexdigest()
                if actual_sha256 != expected_sha256:
                    raise ConanInvalidConfiguration(
                        f"MPICH package has unexpected {name} SHA-256: {actual_sha256}"
                    )

    @staticmethod
    def _package_relative_libdirs(package_folder, libdirs):
        package_root = os.path.realpath(package_folder)
        package_identity = os.path.normcase(package_root)
        normalized = []
        for libdir in libdirs:
            candidate = os.fspath(libdir)
            if not os.path.isabs(candidate):
                candidate = os.path.join(package_root, candidate)
            resolved = os.path.realpath(candidate)
            resolved_identity = os.path.normcase(resolved)
            try:
                contained = (
                    os.path.commonpath((package_identity, resolved_identity))
                    == package_identity
                )
            except ValueError:
                contained = False
            if not contained:
                raise ConanInvalidConfiguration(
                    f"MPICH component library directory escapes package: {libdir}"
                )
            if not os.path.isdir(resolved):
                raise ConanInvalidConfiguration(
                    f"MPICH component library directory does not exist: {libdir}"
                )
            normalized.append(
                os.path.relpath(resolved, package_root).replace(os.sep, "/")
            )
        return normalized

    def _validate_component_contract(self):
        dependency = self._dep()
        components = dependency.cpp_info.components
        contracts = {
            "c": {
                "libs": ["mpi"],
                "cmake_target_name": "MPI::MPI_C",
            },
            "fortran": {
                "libs": [
                    "mpifort",
                    "FortranRuntime",
                    "FortranDecimal",
                    "FortranCommon",
                ],
                "libdirs": ["lib", "lib/flang-runtime"],
                "requires": ["c"],
                "cmake_target_name": "MPI::MPI_Fortran",
            },
        }
        for name, expected in contracts.items():
            try:
                component = components[name]
            except KeyError as error:
                raise ConanInvalidConfiguration(
                    f"missing MPICH Conan component: {name}"
                ) from error
            actual = {
                "libs": list(component.libs),
                "cmake_target_name": component.get_property("cmake_target_name"),
            }
            if name == "fortran":
                actual.update(
                    {
                        "libdirs": self._package_relative_libdirs(
                            dependency.package_folder, component.libdirs
                        ),
                        "requires": list(component.requires),
                    }
                )
            if actual != expected:
                raise ConanInvalidConfiguration(
                    f"invalid MPICH {name} component: expected {expected}, got {actual}"
                )

    def _path(self, name, package_folder=None):
        package_folder = package_folder or self._dep().package_folder
        candidate = os.path.join(package_folder, "bin", name)
        if not os.path.isfile(candidate):
            raise ConanInvalidConfiguration(f"missing MPICH command: {name}")
        return candidate

    def _shell(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell) or not os.access(shell, os.X_OK):
            raise ConanInvalidConfiguration(
                "MPICH tests require the fixed /system/bin/sh target shell"
            )
        return shell

    def _prepare_tmp(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        return tmpdir

    @staticmethod
    def _is_within(path, root):
        if not path or not root:
            return False
        path = os.path.normcase(os.path.realpath(path))
        root = os.path.normcase(os.path.realpath(root))
        try:
            return os.path.commonpath((path, root)) == root
        except ValueError:
            return False

    def _sanitized_path(self, variable, forbidden_roots):
        entries = []
        identities = set()
        for entry in os.environ.get(variable, "").split(os.pathsep):
            if not entry or not os.path.isabs(entry):
                continue
            if any(self._is_within(entry, root) for root in forbidden_roots):
                continue
            identity = os.path.normcase(os.path.realpath(entry))
            if ".conan2" in identity.replace("\\", "/").split("/"):
                continue
            if identity in identities:
                continue
            entries.append(entry)
            identities.add(identity)
        return entries

    @staticmethod
    def _unique_paths(entries):
        result = []
        identities = set()
        for entry in entries:
            identity = os.path.normcase(os.path.realpath(entry))
            if identity in identities:
                continue
            result.append(entry)
            identities.add(identity)
        return result

    def _override_names(self):
        names = set(self._override_exact)
        names.update(
            name
            for name in os.environ
            if self._override_pattern.search(name) and name != "MPIEXEC_TIMEOUT"
        )
        return names

    def _poison_environment(self, label):
        poison_root = os.path.join(self.build_folder, "poison-overrides")
        os.makedirs(poison_root, exist_ok=True)
        marker = os.path.join(poison_root, f"{label}.invoked")
        if os.path.lexists(marker):
            os.unlink(marker)
        script = os.path.join(poison_root, "poison-compiler.sh")
        with open(script, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(
                f"#!/system/bin/sh\nprintf '%s\\n' poison >> {quote(marker)}\nexit 97\n"
            )
        poison_command = f"{self._shell()} {script}"
        invalid_config = os.path.join(poison_root, "invalid-hydra.conf")
        with open(invalid_config, "w", encoding="utf-8", newline="\n") as stream:
            stream.write("this-is-not-a-valid-hydra-option\n")
        poison_home = os.path.join(poison_root, "foreign-home")
        os.makedirs(poison_home, exist_ok=True)
        with open(
            os.path.join(poison_home, ".mpiexec.hydra.conf"),
            "w",
            encoding="utf-8",
            newline="\n",
        ) as stream:
            stream.write("this-is-not-a-valid-hydra-option\n")
        foreign_config = os.path.join(poison_root, "foreign-mpich")
        os.makedirs(foreign_config, exist_ok=True)
        cmake_marker = marker.replace("\\", "/")
        with open(
            os.path.join(foreign_config, "MPICHConfig.cmake"),
            "w",
            encoding="utf-8",
            newline="\n",
        ) as stream:
            stream.write(
                f'file(APPEND "{cmake_marker}" "foreign-mpich-config\\n")\n'
                'message(FATAL_ERROR "foreign MPICHConfig.cmake was loaded")\n'
            )
        invalid_toolchain = os.path.join(poison_root, "foreign-toolchain.cmake")
        with open(invalid_toolchain, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(
                f'file(APPEND "{cmake_marker}" "foreign-toolchain\\n")\n'
                'message(FATAL_ERROR "foreign CMake toolchain was loaded")\n'
            )

        environment = Environment()
        for name in (
            "MPICH_CC",
            "MPICH_CXX",
            "MPICH_FC",
            "MPICC",
            "MPICXX",
            "MPIFC",
            "MPIFORT",
            "MPIEXEC",
        ):
            environment.define(name, poison_command)
        for name in ("MPICC_PROFILE", "MPICXX_PROFILE", "MPIFORT_PROFILE"):
            environment.define(name, "codex-poison-profile")
        environment.define_path("HYDRA_CONFIG_FILE", invalid_config)
        environment.define_path("HOME", poison_home)
        environment.define_path(
            "LD_PRELOAD", os.path.join(poison_root, "libpoison-mpi.so")
        )
        environment.define_path("CPATH", poison_root)
        environment.define_path("LIBRARY_PATH", poison_root)
        environment.define_path("MPICH_DIR", foreign_config)
        environment.define_path("MPI_HOME", poison_root)
        environment.define_path("MPI_ROOT", poison_root)
        environment.define_path("CMAKE_PREFIX_PATH", poison_root)
        environment.define_path("CMAKE_MODULE_PATH", poison_root)
        environment.define_path("CMAKE_FIND_ROOT_PATH", poison_root)
        environment.define_path("CMAKE_FIND_PACKAGE_REDIRECTS_DIR", poison_root)
        environment.define_path("CMAKE_TOOLCHAIN_FILE", invalid_toolchain)
        environment.define_path("CMAKE_PROJECT_TOP_LEVEL_INCLUDES", invalid_toolchain)
        environment.define_path("PKG_CONFIG_PATH", poison_root)
        environment.define_path("PKG_CONFIG_LIBDIR", poison_root)
        environment.define_path("PKG_CONFIG_SYSROOT_DIR", poison_root)
        environment.define("MPIR_CVAR_ALLREDUCE_INTRA_ALGORITHM", "codex-invalid")
        environment.define("MPIR_CVAR_PMI_VERSION", "codex-invalid")
        environment.define("MPIR_PARAM_CH3_PORT_RANGE", "codex-invalid")
        environment.define("PMIX_NAMESPACE", "codex-poison-namespace")
        environment.define("PMI_VERSION", "99")
        environment.define("PMI_SUBVERSION", "99")
        return environment, marker

    def _assert_overrides_cleared(self):
        present = sorted(
            name
            for name in self._override_names()
            if name not in ("HOME", "HYDRA_CONFIG_FILE")
            and os.environ.get(name) is not None
        )
        if present:
            raise ConanInvalidConfiguration(
                "closed MPICH environment retained override variables: "
                + ", ".join(present)
            )
        home = os.environ.get("HOME")
        config = os.environ.get("HYDRA_CONFIG_FILE")
        expected_config = os.path.join(home or "", "mpiexec.hydra.conf")
        if (
            not home
            or os.path.islink(home)
            or not os.path.isdir(home)
            or os.path.commonpath(
                (os.path.realpath(home), os.path.realpath(self.build_folder))
            )
            != os.path.realpath(self.build_folder)
            or not config
            or os.path.islink(config)
            or not os.path.isfile(config)
            or os.path.realpath(config) != os.path.realpath(expected_config)
            or os.path.getsize(config) != 0
        ):
            raise ConanInvalidConfiguration(
                "closed MPICH environment lacks its controlled empty Hydra config"
            )

    def _reject_foreign_mpi(self, paths, library_paths, package_folder):
        selected_bin = os.path.normcase(
            os.path.realpath(os.path.join(package_folder, "bin"))
        )
        foreign_commands = []
        for directory in paths:
            if os.path.normcase(os.path.realpath(directory)) == selected_bin:
                continue
            for name in self._wrapper_names + self._launcher_names:
                candidate = os.path.join(directory, name)
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    foreign_commands.append(candidate)
        if foreign_commands:
            raise ConanInvalidConfiguration(
                "closed MPICH PATH contains foreign commands: "
                + ", ".join(foreign_commands)
            )

        selected_lib = os.path.normcase(
            os.path.realpath(os.path.join(package_folder, "lib"))
        )
        foreign_libraries = []
        for directory in library_paths:
            if os.path.normcase(os.path.realpath(directory)) == selected_lib:
                continue
            foreign_libraries.extend(
                path
                for path in glob.glob(os.path.join(directory, "libmpi.so*"))
                if os.path.isfile(path)
            )
        if foreign_libraries:
            raise ConanInvalidConfiguration(
                "closed MPICH LD_LIBRARY_PATH contains foreign libraries: "
                + ", ".join(foreign_libraries)
            )

    def _configured_compiler_directory(self, key, wrapper_name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = compilers.get(key)
        if not isinstance(configured, str) or not configured.strip():
            raise ConanInvalidConfiguration(
                "MPICH test environment requires "
                f"tools.build:compiler_executables[{key}]"
            )
        try:
            arguments = split(configured)
        except ValueError as error:
            raise ConanInvalidConfiguration(
                f"invalid MPICH {wrapper_name} compiler configuration: {error}"
            ) from error
        if len(arguments) != 1 or not os.path.isabs(arguments[0]):
            raise ConanInvalidConfiguration(
                f"MPICH {wrapper_name} compiler must be one absolute executable path"
            )

        configured_path = os.path.realpath(arguments[0])
        if not os.path.isfile(configured_path):
            raise ConanInvalidConfiguration(
                f"MPICH configured {wrapper_name} compiler is missing: {arguments[0]}"
            )
        directory = os.path.dirname(configured_path)
        wrapper_path = os.path.join(directory, wrapper_name)
        if (
            not os.path.isfile(wrapper_path)
            or os.path.normcase(os.path.realpath(wrapper_path))
            != os.path.normcase(configured_path)
        ):
            raise ConanInvalidConfiguration(
                f"MPICH configured compiler does not bind the {wrapper_name} wrapper"
            )
        return directory

    @contextmanager
    def _closed_environment(self, package_folder, timeout="60"):
        original = self._dep().package_folder
        flang_package = self.dependencies.build["flang-ohos"].package_folder
        flang = os.path.join(flang_package, "bin", "flang")
        if not os.path.isfile(flang):
            raise ConanInvalidConfiguration("flang-ohos compiler is missing")
        compiler_paths = [
            self._configured_compiler_directory("c", "clang"),
            self._configured_compiler_directory("cpp", "clang++"),
        ]

        forbidden = (
            original,
            package_folder,
            flang_package,
            "/storage/Users/currentUser/usr/local",
        )
        paths = [
            os.path.join(package_folder, "bin"),
            os.path.join(flang_package, "bin"),
        ]
        paths.extend(compiler_paths)
        paths.extend(self._sanitized_path("PATH", forbidden))
        paths = self._unique_paths(paths)
        library_paths = [
            os.path.join(package_folder, "lib"),
            os.path.join(flang_package, "lib"),
        ]
        library_paths.extend(self._sanitized_path("LD_LIBRARY_PATH", forbidden))
        library_paths = self._unique_paths(library_paths)

        if os.path.realpath(package_folder) != os.path.realpath(original):
            leaked = [
                entry
                for entry in paths + library_paths
                if self._is_within(entry, original)
            ]
            if leaked:
                raise ConanInvalidConfiguration(
                    "relocated environment contains original package paths: "
                    + ", ".join(leaked)
                )
        self._reject_foreign_mpi(paths, library_paths, package_folder)

        tmpdir = self._prepare_tmp()
        identity = hashlib.sha256(
            os.path.realpath(package_folder).encode("utf-8")
        ).hexdigest()[:16]
        safe_home = os.path.join(self.build_folder, f"closed-home-{identity}")
        if os.path.lexists(safe_home):
            if os.path.islink(safe_home) or not os.path.isdir(safe_home):
                os.unlink(safe_home)
            else:
                shutil.rmtree(safe_home)
        os.makedirs(safe_home, mode=0o700)
        safe_hydra_config = os.path.join(safe_home, "mpiexec.hydra.conf")
        with open(safe_hydra_config, "x", encoding="utf-8", newline="\n") as stream:
            stream.write("")
        controlled = {
            "PATH": os.pathsep.join(paths),
            "LD_LIBRARY_PATH": os.pathsep.join(library_paths),
            "TMPDIR": tmpdir,
            "TMPPREFIX": os.path.join(tmpdir, "sh"),
            "SHELL": self._shell(),
            "CONFIG_SHELL": self._shell(),
            "HOME": safe_home,
            "HYDRA_CONFIG_FILE": safe_hydra_config,
            "MPIEXEC_TIMEOUT": timeout,
        }
        original = os.environ.copy()
        try:
            for name in self._override_names():
                os.environ.pop(name, None)
            os.environ.update(controlled)
            yield
        finally:
            os.environ.clear()
            os.environ.update(original)

    def _validate_closed_environment_transaction(self, package_folder):
        original = os.environ.copy()
        poison = {
            "MPICH_CC": "codex-poison-compiler",
            "MPIR_CVAR_PMI_VERSION": "codex-poison-cvar",
            "LD_PRELOAD": "codex-poison-library",
        }
        try:
            os.environ.update(poison)
            poisoned = os.environ.copy()
            with self._closed_environment(package_folder):
                self._assert_overrides_cleared()
                retained = sorted(name for name in poison if name in os.environ)
                if retained:
                    raise ConanInvalidConfiguration(
                        "closed MPICH environment retained poisoned keys: "
                        + ", ".join(retained)
                    )
            if os.environ != poisoned:
                raise ConanInvalidConfiguration(
                    "closed MPICH environment did not restore its normal exit"
                )

            try:
                with self._closed_environment(package_folder):
                    self._assert_overrides_cleared()
                    raise RuntimeError("closed-environment-exception-probe")
            except RuntimeError as error:
                if str(error) != "closed-environment-exception-probe":
                    raise
            if os.environ != poisoned:
                raise ConanInvalidConfiguration(
                    "closed MPICH environment did not restore its exceptional exit"
                )
        finally:
            os.environ.clear()
            os.environ.update(original)

    def _validate_wrapper_diagnostics(self, wrappers, package_folder):
        diagnostics = {}
        expected_compilers = {
            "mpicc": "clang",
            "mpicxx": "clang++",
            "mpic++": "clang++",
            "mpifort": "flang",
            "mpif77": "flang",
            "mpif90": "flang",
        }
        for name, wrapper in wrappers.items():
            outputs = []
            for option in ("-show", "-compile-info", "-link-info"):
                try:
                    result = subprocess.run(
                        [wrapper, option],
                        cwd=self.build_folder,
                        env=os.environ.copy(),
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                except (OSError, subprocess.TimeoutExpired) as error:
                    raise ConanInvalidConfiguration(
                        f"cannot inspect {name} {option}: {error}"
                    ) from error
                if result.returncode != 0:
                    raise ConanInvalidConfiguration(
                        f"{name} {option} failed: {result.stderr.strip()}"
                    )
                outputs.append(result.stdout.strip())
            diagnostics[name] = "\n".join(outputs).replace("\\", "/")

        include = os.path.join(package_folder, "include").replace("\\", "/")
        lib = os.path.join(package_folder, "lib").replace("\\", "/")
        original = self._dep().package_folder.replace("\\", "/")
        for name, output in diagnostics.items():
            compiler = expected_compilers[name]
            if not re.search(rf"(?:^|\s){re.escape(compiler)}(?:\s|$)", output):
                raise ConanInvalidConfiguration(
                    f"{name} diagnostics do not select {compiler}: {output}"
                )
            if f"-I{include}" not in output or f"-L{lib}" not in output:
                raise ConanInvalidConfiguration(
                    f"{name} diagnostics do not bind selected include/lib paths"
                )
            if "codex-poison" in output:
                raise ConanInvalidConfiguration(
                    f"{name} diagnostics retained a poison profile"
                )
            if (
                os.path.realpath(package_folder)
                != os.path.realpath(self._dep().package_folder)
                and original in output
            ):
                raise ConanInvalidConfiguration(
                    f"relocated {name} diagnostics reference the original package"
                )
            for forbidden in ("/.conan2/", "/storage/Users/currentUser/usr/local/"):
                if forbidden in output:
                    raise ConanInvalidConfiguration(
                        f"{name} diagnostics contain forbidden path {forbidden}"
                    )

    def _compile(self, package_folder, suffix=""):
        wrappers = {
            name: self._path(name, package_folder) for name in self._wrapper_names
        }
        source = self.source_folder
        commands = (
            f"{quote(wrappers['mpicc'])} {quote(os.path.join(source, 'test.c'))} "
            f"-o test_mpi_c{suffix}",
            f"{quote(wrappers['mpicxx'])} "
            f"{quote(os.path.join(source, 'test.cxx'))} "
            f"-o test_mpi_cxx{suffix}",
            f"{quote(wrappers['mpic++'])} "
            f"{quote(os.path.join(source, 'test.cxx'))} "
            f"-o test_mpi_cpp_alias{suffix}",
            f"{quote(wrappers['mpif77'])} "
            f"{quote(os.path.join(source, 'test_mpifh.f'))} "
            f"-o test_mpifh{suffix}",
            f"{quote(wrappers['mpif90'])} "
            f"{quote(os.path.join(source, 'test_use_mpi.f90'))} "
            f"-o test_use_mpi{suffix}",
            f"{quote(wrappers['mpicc'])} -c "
            f"{quote(os.path.join(source, 'test_mixed.c'))} "
            f"-o test_mixed_c{suffix}.o",
            f"{quote(wrappers['mpifort'])} "
            f"{quote(os.path.join(source, 'test_mixed.f90'))} "
            f"test_mixed_c{suffix}.o -o test_mixed{suffix}",
            f"{quote(wrappers['mpifort'])} -fdefault-integer-8 "
            f"{quote(os.path.join(source, 'test_nwchem_mpif4_bridge.f'))} "
            f"-o test_nwchem_mpif4_bridge{suffix}",
            f"{quote(wrappers['mpicc'])} "
            f"{quote(os.path.join(source, 'test_process_control.c'))} "
            f"-o test_process_control{suffix}",
            f"{quote(wrappers['mpicc'])} "
            f"{quote(os.path.join(source, 'test_pmi_malformed_abort.c'))} "
            f"-o test_pmi_malformed_abort{suffix}",
        )
        commands += (
            f"{quote(wrappers['mpifort'])} -c "
            f"{quote(os.path.join(source, 'cmake_fortran_probe.f90'))} "
            f"-o {quote(os.path.join(self.build_folder, f'cmake_fortran_probe{suffix}.o'))}",
        )
        poison, marker = self._poison_environment(
            "original" if not suffix else "relocated"
        )
        with poison.vars(self).apply():
            with self._closed_environment(package_folder):
                self._assert_overrides_cleared()
                self._validate_wrapper_diagnostics(wrappers, package_folder)
                for command in commands:
                    self.run(command, cwd=self.build_folder, env=None)
        if os.path.exists(marker):
            raise ConanInvalidConfiguration(
                f"closed MPICH compiler environment invoked poison marker {marker}"
            )

    def _package_topology(self, root):
        symlinks = {}
        hardlink_members = {}
        hardlink_counts = {}
        for directory, dirnames, filenames in os.walk(
            root, topdown=True, followlinks=False
        ):
            linked_directories = [
                name
                for name in dirnames
                if os.path.islink(os.path.join(directory, name))
            ]
            dirnames[:] = [name for name in dirnames if name not in linked_directories]
            for name in filenames + linked_directories:
                path = os.path.join(directory, name)
                relative = os.path.relpath(path, root)
                if os.path.islink(path):
                    target = os.readlink(path)
                    if os.path.isabs(target):
                        raise ConanInvalidConfiguration(
                            f"absolute package symlink is forbidden: {relative} -> {target}"
                        )
                    resolved = os.path.realpath(path)
                    if not self._is_within(resolved, root) or not os.path.exists(
                        resolved
                    ):
                        raise ConanInvalidConfiguration(
                            f"escaping or cyclic package symlink: {relative} -> {target}"
                        )
                    symlinks[relative] = target
                    continue
                if not os.path.isfile(path):
                    continue
                metadata = os.stat(path, follow_symlinks=False)
                identity = (metadata.st_dev, metadata.st_ino)
                hardlink_members.setdefault(identity, []).append(relative)
                hardlink_counts[identity] = metadata.st_nlink

        internal_hardlinks = []
        for identity, members in hardlink_members.items():
            members = tuple(sorted(members))
            if hardlink_counts[identity] != len(members):
                raise ConanInvalidConfiguration(
                    "package contains hardlink evidence outside its root: "
                    + ", ".join(members)
                )
            if len(members) > 1:
                internal_hardlinks.append(members)
        return symlinks, tuple(sorted(internal_hardlinks))

    def _copytree_preserving_topology(self, source, destination):
        expected_symlinks, expected_hardlinks = self._package_topology(source)
        shutil.copytree(
            source,
            destination,
            symlinks=True,
            dirs_exist_ok=False,
        )
        for members in expected_hardlinks:
            first = os.path.join(destination, members[0])
            for relative in members[1:]:
                path = os.path.join(destination, relative)
                os.unlink(path)
                os.link(first, path)
        actual_symlinks, actual_hardlinks = self._package_topology(destination)
        if actual_symlinks != expected_symlinks:
            raise ConanInvalidConfiguration(
                "relocation changed the MPICH symlink topology"
            )
        if actual_hardlinks != expected_hardlinks:
            raise ConanInvalidConfiguration(
                "relocation changed the MPICH hardlink topology"
            )

    def _expect_topology_rejection(self, root, label):
        try:
            self._package_topology(root)
        except ConanInvalidConfiguration:
            return
        raise ConanInvalidConfiguration(f"package topology validator accepted {label}")

    @staticmethod
    def _topology_fixture_unavailable(error_number):
        return error_number in {
            errno.EACCES,
            errno.EPERM,
            errno.ENOSYS,
            errno.ENOTSUP,
            getattr(errno, "EOPNOTSUPP", errno.ENOTSUP),
        }

    def _validate_topology_negatives(self):
        fixture = os.path.join(self.build_folder, "topology-negatives")
        if os.path.lexists(fixture):
            shutil.rmtree(fixture)
        os.makedirs(fixture)
        outside = os.path.join(fixture, "outside.bin")
        with open(outside, "wb") as stream:
            stream.write(b"mpich-topology-negative\n")

        link_supported = True
        absolute_root = os.path.join(fixture, "absolute")
        os.makedirs(absolute_root)
        try:
            os.symlink(outside, os.path.join(absolute_root, "escape"))
        except OSError as error:
            if not self._topology_fixture_unavailable(error.errno):
                raise
            link_supported = False
        if link_supported:
            self._expect_topology_rejection(absolute_root, "absolute symlink")

            relative_root = os.path.join(fixture, "relative")
            os.makedirs(relative_root)
            os.symlink("../outside.bin", os.path.join(relative_root, "escape"))
            self._expect_topology_rejection(relative_root, "relative escape symlink")

            cycle_root = os.path.join(fixture, "cycle")
            os.makedirs(cycle_root)
            os.symlink("loop-b", os.path.join(cycle_root, "loop-a"))
            os.symlink("loop-a", os.path.join(cycle_root, "loop-b"))
            self._expect_topology_rejection(cycle_root, "cyclic symlink")

            internal_root = os.path.join(fixture, "internal-link")
            os.makedirs(internal_root)
            with open(os.path.join(internal_root, "target"), "wb") as stream:
                stream.write(b"internal-link\n")
            os.symlink("target", os.path.join(internal_root, "link"))
            links, _hardlinks = self._package_topology(internal_root)
            if links != {"link": "target"}:
                raise ConanInvalidConfiguration(
                    "package topology validator rejected a bound internal symlink"
                )

        hardlink_root = os.path.join(fixture, "external-hardlink")
        os.makedirs(hardlink_root)
        try:
            os.link(outside, os.path.join(hardlink_root, "escape"))
        except OSError as error:
            if not self._topology_fixture_unavailable(error.errno):
                raise
        else:
            self._expect_topology_rejection(hardlink_root, "external hardlink evidence")

        internal_hardlink_root = os.path.join(fixture, "internal-hardlink")
        os.makedirs(internal_hardlink_root)
        base = os.path.join(internal_hardlink_root, "base")
        alias = os.path.join(internal_hardlink_root, "alias")
        with open(base, "wb") as stream:
            stream.write(b"internal-hardlink\n")
        try:
            os.link(base, alias)
        except OSError as error:
            if not self._topology_fixture_unavailable(error.errno):
                raise
        else:
            _links, hardlinks = self._package_topology(internal_hardlink_root)
            if hardlinks != (("alias", "base"),):
                raise ConanInvalidConfiguration(
                    "package topology validator lost an internal hardlink"
                )

    def _relocated_package(self):
        relocated = os.path.join(self.build_folder, "relocated-mpich")
        if os.path.exists(relocated):
            shutil.rmtree(relocated)
        self._copytree_preserving_topology(self._dep().package_folder, relocated)
        forbidden = (
            self._dep().package_folder,
            self.build_folder,
            ".conan2",
            "/storage/Users/currentUser/usr/local",
        )
        for name in self._wrapper_names:
            wrapper = self._path(name, relocated)
            with open(wrapper, "rb") as stream:
                if stream.read(4) != b"\x7fELF":
                    raise ConanInvalidConfiguration(
                        f"relocated {name} is not an executable ELF launcher"
                    )
            script = self._path(f"{name}.sh", relocated)
            with open(script, "r", encoding="utf-8") as stream:
                content = stream.read()
            leaks = [value for value in forbidden if value and value in content]
            if leaks:
                raise ConanInvalidConfiguration(
                    f"relocated {name} contains forbidden paths: {', '.join(leaks)}"
                )
        for name in self._launcher_names:
            executable = self._path(name, relocated)
            with open(executable, "rb") as stream:
                if stream.read(4) != b"\x7fELF":
                    raise ConanInvalidConfiguration(
                        f"relocated {name} is not an executable ELF"
                    )
        return relocated

    @staticmethod
    def _replace_cmake_package_prefix(content, original, relocated):
        if not original or original == relocated or relocated in content:
            raise ConanInvalidConfiguration(
                "invalid MPICH CMake relocation prefix transaction"
            )
        count = content.count(original)
        if count == 0:
            raise ConanInvalidConfiguration(
                "MPICH CMake generator is missing the original package prefix"
            )
        rewritten = content.replace(original, relocated)
        if original in rewritten or rewritten.count(relocated) < count:
            raise ConanInvalidConfiguration(
                "MPICH CMake generator relocation post-image changed"
            )
        return rewritten, count

    @classmethod
    def _validate_cmake_relocation_rewrite_guard(cls):
        original = "/candidate/original"
        relocated = "/candidate/relocated"
        baseline = f"prefix={original}\nlink={original}/lib/libmpi.so\n"
        rewritten, count = cls._replace_cmake_package_prefix(
            baseline, original, relocated
        )
        if count != 2 or original in rewritten or rewritten.count(relocated) != 2:
            raise ConanInvalidConfiguration(
                "MPICH CMake relocation rewrite positive contract changed"
            )
        mutations = (
            baseline.replace(original, "/candidate/missing"),
            baseline.replace(original, relocated),
        )
        for mutation in mutations:
            try:
                cls._replace_cmake_package_prefix(mutation, original, relocated)
            except ConanInvalidConfiguration:
                continue
            raise ConanInvalidConfiguration(
                "MPICH CMake relocation rewrite negative mutation was accepted"
            )
        try:
            cls._replace_cmake_package_prefix(baseline, original, original)
        except ConanInvalidConfiguration:
            return
        raise ConanInvalidConfiguration(
            "MPICH CMake relocation accepted identical prefixes"
        )

    @contextmanager
    def _relocated_cmake_generators(self, relocated):
        original = os.path.realpath(self._dep().package_folder)
        relocated = os.path.realpath(relocated)
        backups = {}
        replacements = 0
        changed = []
        try:
            for root, directories, files in os.walk(self.generators_folder):
                directories.sort()
                for name in sorted(files):
                    path = os.path.join(root, name)
                    try:
                        with open(path, "r", encoding="utf-8") as stream:
                            content = stream.read()
                    except UnicodeDecodeError:
                        continue
                    if original not in content:
                        continue
                    rewritten, count = self._replace_cmake_package_prefix(
                        content, original, relocated
                    )
                    with open(path, "rb") as stream:
                        backups[path] = stream.read()
                    with open(path, "w", encoding="utf-8", newline="\n") as stream:
                        stream.write(rewritten)
                    replacements += count
                    changed.append(path)
            if replacements == 0 or not changed:
                raise ConanInvalidConfiguration(
                    "no generated MPICH CMake dependency path was relocated"
                )
            for path in changed:
                with open(path, "r", encoding="utf-8") as stream:
                    content = stream.read()
                if original in content or relocated not in content:
                    raise ConanInvalidConfiguration(
                        f"relocated MPICH CMake generator changed: {path}"
                    )
            yield {
                "files": len(changed),
                "replacements": replacements,
                "original": original,
                "relocated": relocated,
            }
        finally:
            for path, content in backups.items():
                with open(path, "wb") as stream:
                    stream.write(content)

    def _reset_cmake_build_state(self):
        for name in (
            "CMakeCache.txt",
            "Makefile",
            "build.ninja",
            "cmake_install.cmake",
        ):
            path = os.path.join(self.build_folder, name)
            if os.path.lexists(path):
                os.unlink(path)
        cmake_files = os.path.join(self.build_folder, "CMakeFiles")
        if os.path.lexists(cmake_files):
            shutil.rmtree(cmake_files)

    def _validate_relocated_cmake_build(self, transaction):
        records = [os.path.join(self.build_folder, "CMakeCache.txt")]
        records.extend(
            sorted(
                path
                for path in glob.glob(
                    os.path.join(self.build_folder, "CMakeFiles", "**", "link.txt"),
                    recursive=True,
                )
                if os.path.isfile(path)
            )
        )
        if len(records) < 3 or any(not os.path.isfile(path) for path in records):
            raise ConanInvalidConfiguration(
                "relocated MPICH CMake build records are incomplete"
            )
        record_contents = []
        for path in records:
            with open(path, "r", encoding="utf-8") as stream:
                record_contents.append(stream.read())
        content = "\n".join(record_contents)
        if transaction["original"] in content:
            raise ConanInvalidConfiguration(
                "relocated MPICH CMake build retained the original package prefix"
            )
        if transaction["relocated"] not in content:
            raise ConanInvalidConfiguration(
                "relocated MPICH CMake build did not use the relocated package prefix"
            )
        for name in ("cmake_mpi_c_relocated", "cmake_mpi_fortran_relocated"):
            if not os.path.isfile(os.path.join(self.build_folder, name)):
                raise ConanInvalidConfiguration(
                    f"relocated MPICH CMake consumer is missing: {name}"
                )

    def _build_cmake_consumers(self, package_folder, suffix=""):
        if suffix not in ("", "_relocated"):
            raise ConanInvalidConfiguration(
                f"unexpected MPICH CMake consumer suffix: {suffix}"
            )
        relocated = os.path.realpath(package_folder) != os.path.realpath(
            self._dep().package_folder
        )
        if relocated != bool(suffix):
            raise ConanInvalidConfiguration(
                "MPICH CMake package prefix and executable suffix disagree"
            )
        transaction_context = (
            self._relocated_cmake_generators(package_folder)
            if relocated
            else nullcontext(None)
        )
        if relocated:
            self._reset_cmake_build_state()
        poison, marker = self._poison_environment(
            "cmake-components" if not suffix else "cmake-components-relocated"
        )
        with transaction_context as transaction:
            with poison.vars(self).apply():
                with self._closed_environment(package_folder):
                    self._assert_overrides_cleared()
                    cmake = CMake(self)
                    cmake.configure(
                        variables={
                            "MPICH_EXECUTABLE_SUFFIX": suffix,
                            "MPICH_FORTRAN_OBJECT": os.path.join(
                                self.build_folder,
                                f"cmake_fortran_probe{suffix}.o",
                            ),
                        }
                    )
                    cmake.build()
            if relocated:
                self._validate_relocated_cmake_build(transaction)
        if os.path.exists(marker):
            raise ConanInvalidConfiguration(
                "closed CMake component environment invoked a foreign provider: "
                + marker
            )

    @classmethod
    def _malformed_abort_probe_is_guarded(cls, content):
        positions = []
        for fragment in cls._malformed_abort_probe_fragments:
            if content.count(fragment) != 1:
                return False
            positions.append(content.index(fragment))
        return positions == sorted(positions)

    def _validate_malformed_abort_probe_contract(self):
        path = os.path.join(self.source_folder, "test_pmi_malformed_abort.c")
        try:
            with open(path, "r", encoding="utf-8") as stream:
                content = stream.read()
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"cannot read malformed PMI abort probe contract: {error}"
            ) from error
        if not self._malformed_abort_probe_is_guarded(content):
            raise ConanInvalidConfiguration(
                "malformed PMI abort probe coverage or structured evidence is incomplete"
            )
        for fragment in self._malformed_abort_probe_fragments:
            mutation = content.replace(fragment, "", 1)
            if self._malformed_abort_probe_is_guarded(mutation):
                raise ConanInvalidConfiguration(
                    "malformed PMI abort probe negative mutation was not rejected"
                )

    def build(self):
        self._prepare_tmp()
        self._validate_malformed_abort_probe_contract()
        self._validate_component_contract()
        self._validate_topology_negatives()
        self._validate_closed_environment_transaction(self._dep().package_folder)
        self._validate_process_environ_race_contract()
        self._validate_cmake_relocation_rewrite_guard()
        self._compile(self._dep().package_folder)
        self._build_cmake_consumers(self._dep().package_folder)
        relocated = self._relocated_package()
        self._compile(relocated, suffix="_relocated")
        self._build_cmake_consumers(relocated, suffix="_relocated")

    @staticmethod
    def _process_identity(pid):
        try:
            with open(f"/proc/{pid}/stat", "r", encoding="utf-8") as stream:
                stat_line = stream.read()
            tail = stat_line[stat_line.rfind(")") + 2 :].split()
            if len(tail) < 20:
                return None
            with open(f"/proc/{pid}/cmdline", "rb") as stream:
                command = (
                    stream.read().split(b"\0", 1)[0].decode("utf-8", errors="replace")
                )
            return (
                int(pid),
                int(tail[1]),
                int(tail[2]),
                tail[19],
                os.path.basename(command),
                tail[0],
            )
        except (OSError, ValueError):
            return None

    def _process_tree(self, root_pid):
        identities = {}
        children = {}
        try:
            names = os.listdir("/proc")
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"cannot inspect /proc for MPI residue: {error}"
            ) from error
        for name in names:
            if not name.isdigit():
                continue
            identity = self._process_identity(int(name))
            if identity is None:
                continue
            identities[identity[0]] = identity
            children.setdefault(identity[1], []).append(identity[0])

        selected = {}
        pending = [root_pid]
        while pending:
            pid = pending.pop()
            identity = identities.get(pid)
            if identity is None or pid in selected:
                continue
            selected[pid] = identity
            pending.extend(children.get(pid, ()))
        return selected

    def _process_group(self, process_group):
        selected = {}
        try:
            names = os.listdir("/proc")
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"cannot inspect /proc for MPI process group: {error}"
            ) from error
        for name in names:
            if not name.isdigit():
                continue
            identity = self._process_identity(int(name))
            if identity is not None and identity[2] == process_group:
                selected[identity[0]] = identity
        return selected

    @staticmethod
    def _ignore_process_environ_error(error_number, before, after):
        if error_number in (errno.EACCES, errno.ENOENT, errno.EPERM, errno.ESRCH):
            return True
        return error_number == errno.EINVAL and (
            after is None or before[3] != after[3] or after[5] == "Z"
        )

    @classmethod
    def _validate_process_environ_race_contract(cls):
        before = (71, 1, 71, "100", "rank", "R")
        cases = (
            ("vanished", errno.EINVAL, before, None, True),
            (
                "pid-reused",
                errno.EINVAL,
                before,
                (71, 1, 71, "101", "other", "R"),
                True,
            ),
            (
                "zombie",
                errno.EINVAL,
                before,
                (71, 1, 71, "100", "rank", "Z"),
                True,
            ),
            (
                "stable-non-zombie",
                errno.EINVAL,
                before,
                (71, 1, 71, "100", "rank", "S"),
                False,
            ),
            (
                "unrelated-error",
                errno.EIO,
                before,
                (71, 1, 71, "100", "rank", "S"),
                False,
            ),
        )
        for label, error_number, old, new, expected in cases:
            actual = cls._ignore_process_environ_error(error_number, old, new)
            if actual != expected:
                raise ConanInvalidConfiguration(
                    f"process environ race contract changed for {label}: {actual}"
                )

    def _token_processes(self, token):
        expected = f"{self._run_token_name}={token}".encode("utf-8")
        selected = {}
        try:
            names = os.listdir("/proc")
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"cannot inspect /proc for MPI run token: {error}"
            ) from error
        for name in names:
            if not name.isdigit():
                continue
            pid = int(name)
            before = self._process_identity(pid)
            if before is None:
                continue
            try:
                with open(f"/proc/{pid}/environ", "rb") as stream:
                    fields = stream.read().split(b"\0")
            except OSError as error:
                after = self._process_identity(pid)
                if self._ignore_process_environ_error(error.errno, before, after):
                    continue
                raise ConanInvalidConfiguration(
                    f"cannot inspect environment for process {pid}: {error}"
                ) from error
            after = self._process_identity(pid)
            if (
                after is not None
                and before[0] == after[0]
                and before[3] == after[3]
                and expected in fields
            ):
                selected[pid] = after
        return selected

    @staticmethod
    def _identity_is_live(identity):
        current = TestPackageConan._process_identity(identity[0])
        return current is not None and current[3] == identity[3]

    @classmethod
    def _root_owns_group(cls, root_identity):
        if root_identity is None or root_identity[2] != root_identity[0]:
            return False
        current = cls._process_identity(root_identity[0])
        return (
            current is not None
            and current[2] == root_identity[2]
            and current[3] == root_identity[3]
        )

    @classmethod
    def _signal_identity(cls, identity, signal_number):
        if not cls._identity_is_live(identity):
            return
        try:
            os.kill(identity[0], signal_number)
        except OSError as error:
            if error.errno != errno.ESRCH:
                raise ConanInvalidConfiguration(
                    f"cannot signal MPI pid {identity[0]}: {error}"
                ) from error

    @classmethod
    def _signal_group(cls, root_identity, signal_number):
        if not cls._root_owns_group(root_identity):
            return
        try:
            os.killpg(root_identity[2], signal_number)
        except OSError as error:
            if error.errno != errno.ESRCH:
                raise ConanInvalidConfiguration(
                    f"cannot signal MPI process group {root_identity[2]}: {error}"
                ) from error

    def _refresh_identities(self, process, identities, token, root_identity):
        owns_group = self._root_owns_group(root_identity)
        if owns_group:
            identities.update(self._process_tree(process.pid))
            identities.update(self._process_group(root_identity[2]))
        identities.update(self._token_processes(token))
        return identities

    @staticmethod
    def _assert_observation_gate_file(path, token):
        expected = f"{token}\n".encode("ascii")
        try:
            with open(path, "rb") as stream:
                actual = stream.read()
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"cannot read MPI observation gate {path}: {error}"
            ) from error
        if actual != expected:
            raise ConanInvalidConfiguration(
                f"MPI observation gate content changed for {path}"
            )

    def _try_publish_observation_gate(self, gate, identities):
        release_file = gate["release_file"]
        token = gate["token"]
        if os.path.lexists(release_file):
            self._assert_observation_gate_file(release_file, token)
            return True

        pid_file = gate["pid_file"]
        expected_roles = tuple(sorted(gate["expected_roles"]))
        try:
            with open(pid_file, "rb") as stream:
                raw_records = stream.read()
        except FileNotFoundError:
            return False
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"cannot inspect MPI observation records {pid_file}: {error}"
            ) from error
        if (
            not raw_records.endswith(b"\n")
            or raw_records.count(b"\n") < len(expected_roles)
        ):
            return False

        records = self._load_role_rank_records(pid_file, "MPI observation gate")
        if tuple(sorted(records)) != expected_roles:
            return False
        live = self._live_identities(identities)
        for pid, process_group in records.values():
            identity = live.get(pid)
            if identity is None or identity[2] != process_group:
                return False
        proxy_count = sum(
            identity[4] == "hydra_pmi_proxy" for identity in live.values()
        )
        if proxy_count != gate["expected_proxies"]:
            return False

        payload = f"{token}\n".encode("ascii")
        try:
            fd = os.open(
                release_file,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_BINARY", 0),
                0o600,
            )
        except FileExistsError:
            self._assert_observation_gate_file(release_file, token)
            return True
        try:
            offset = 0
            while offset < len(payload):
                written = os.write(fd, payload[offset:])
                if written <= 0:
                    raise OSError(errno.EIO, "short MPI observation gate write")
                offset += written
            os.fsync(fd)
        finally:
            os.close(fd)
        self._assert_observation_gate_file(release_file, token)
        return True

    @staticmethod
    def _append_cleanup_error(errors, label, error):
        message = f"{label}: {type(error).__name__}: {error}"
        if message not in errors:
            errors.append(message)

    def _refresh_cleanup_identities(
        self, process, identities, token, root_identity, errors
    ):
        owns_group = self._root_owns_group(root_identity)
        scanners = []
        if owns_group:
            scanners.extend(
                (
                    ("process-tree scan", self._process_tree, process.pid),
                    ("process-group scan", self._process_group, root_identity[2]),
                )
            )
        scanners.append(("run-token scan", self._token_processes, token))
        for label, scanner, argument in scanners:
            try:
                identities.update(scanner(argument))
            except Exception as error:
                self._append_cleanup_error(errors, label, error)
        return identities

    def _bind_launcher_identity(self, process, identities, token, initial_identity):
        deadline = time.monotonic() + 0.25
        root_identity = initial_identity
        while True:
            if root_identity is None:
                root_identity = self._process_identity(process.pid)
            token_processes = self._token_processes(token)
            identities.update(token_processes)
            if (
                root_identity is not None
                and root_identity[2] == process.pid
                and process.pid in token_processes
                and token_processes[process.pid][3] == root_identity[3]
            ):
                return root_identity
            if process.poll() is not None:
                return None
            if time.monotonic() >= deadline:
                raise ConanInvalidConfiguration(
                    "cannot bind managed MPI launcher identity"
                )
            time.sleep(0.01)
            root_identity = self._process_identity(process.pid)

    def _cleanup_processes(self, process, identities, token, root_identity):
        cleanup_errors = []
        self._refresh_cleanup_identities(
            process, identities, token, root_identity, cleanup_errors
        )
        try:
            self._signal_group(root_identity, signal.SIGTERM)
        except Exception as error:
            self._append_cleanup_error(
                cleanup_errors, "process-group SIGTERM", error
            )
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            self._refresh_cleanup_identities(
                process, identities, token, root_identity, cleanup_errors
            )
            live = self._live_identities(identities)
            if not live:
                break
            for identity in live.values():
                try:
                    self._signal_identity(identity, signal.SIGTERM)
                except Exception as error:
                    self._append_cleanup_error(
                        cleanup_errors, f"pid {identity[0]} SIGTERM", error
                    )
            time.sleep(0.05)

        self._refresh_cleanup_identities(
            process, identities, token, root_identity, cleanup_errors
        )
        live = self._live_identities(identities)
        if live:
            try:
                self._signal_group(root_identity, signal.SIGKILL)
            except Exception as error:
                self._append_cleanup_error(
                    cleanup_errors, "process-group SIGKILL", error
                )
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                self._refresh_cleanup_identities(
                    process, identities, token, root_identity, cleanup_errors
                )
                live = self._live_identities(identities)
                if not live:
                    break
                for identity in live.values():
                    try:
                        self._signal_identity(identity, signal.SIGKILL)
                    except Exception as error:
                        self._append_cleanup_error(
                            cleanup_errors, f"pid {identity[0]} SIGKILL", error
                        )
                time.sleep(0.05)

        if process.poll() is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            except Exception as error:
                self._append_cleanup_error(
                    cleanup_errors, "launcher SIGKILL", error
                )
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._append_cleanup_error(
                cleanup_errors,
                "launcher reap",
                ConanInvalidConfiguration(
                    f"cannot reap managed MPI launcher pid {process.pid}"
                ),
            )
        remaining = self._wait_for_zero_residue(
            identities,
            process=process,
            token=token,
            root_identity=root_identity,
            cleanup_errors=cleanup_errors,
        )
        if remaining or cleanup_errors:
            details = []
            if remaining:
                details.append(
                    "residue="
                    + ", ".join(
                        f"pid={item[0]} command={item[4]}"
                        for item in remaining.values()
                    )
                )
            if cleanup_errors:
                details.append("errors=" + " | ".join(cleanup_errors))
            raise ConanInvalidConfiguration(
                "managed MPI cleanup did not close cleanly: " + "; ".join(details)
            )

    def _wait_for_zero_residue(
        self,
        identities,
        timeout=5,
        process=None,
        token=None,
        root_identity=None,
        cleanup_errors=None,
    ):
        deadline = time.monotonic() + timeout
        empty_scans = 0
        while time.monotonic() < deadline:
            if process is not None and token is not None:
                if cleanup_errors is None:
                    self._refresh_identities(
                        process, identities, token, root_identity
                    )
                else:
                    self._refresh_cleanup_identities(
                        process,
                        identities,
                        token,
                        root_identity,
                        cleanup_errors,
                    )
            live = self._live_identities(identities)
            if not live:
                empty_scans += 1
                if empty_scans == 2:
                    return {}
            else:
                empty_scans = 0
            time.sleep(0.05)
        if process is not None and token is not None:
            if cleanup_errors is None:
                self._refresh_identities(process, identities, token, root_identity)
            else:
                self._refresh_cleanup_identities(
                    process, identities, token, root_identity, cleanup_errors
                )
        return self._live_identities(identities)

    def _assert_zero_residue(
        self, identities, process=None, token=None, root_identity=None
    ):
        live = self._wait_for_zero_residue(
            identities,
            process=process,
            token=token,
            root_identity=root_identity,
        )
        if live:
            raise ConanInvalidConfiguration(
                "MPI execution left process residue: "
                + ", ".join(
                    f"pid={item[0]} command={item[4]}" for item in live.values()
                )
            )

    def _live_identities(self, identities):
        return {
            pid: identity
            for pid, identity in identities.items()
            if self._identity_is_live(identity)
        }

    @staticmethod
    def _attach_cleanup_failure(error, cleanup_error):
        note = f"managed MPI process cleanup also failed: {cleanup_error}"
        if hasattr(error, "add_note"):
            error.add_note(note)
        else:
            error.args = (*error.args, note)

    def _run_managed_mpi(
        self,
        command,
        outer_timeout,
        require_launcher_cleanup=False,
        observation_gate=None,
    ):
        process = None
        identities = {}
        root_identity = None
        token = secrets.token_hex(32)
        observation_gate_published = observation_gate is None
        try:
            process_environment = os.environ.copy()
            process_environment[self._run_token_name] = token
            process = subprocess.Popen(
                command,
                cwd=self.build_folder,
                env=process_environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
            root_identity = self._process_identity(process.pid)
            root_identity = self._bind_launcher_identity(
                process, identities, token, root_identity
            )
            deadline = time.monotonic() + outer_timeout
            timed_out = False
            while process.poll() is None:
                self._refresh_identities(process, identities, token, root_identity)
                if not observation_gate_published:
                    observation_gate_published = self._try_publish_observation_gate(
                        observation_gate, identities
                    )
                if time.monotonic() >= deadline:
                    timed_out = True
                    break
                time.sleep(0.05)
            if timed_out:
                if require_launcher_cleanup:
                    live = self._live_identities(identities)
                    if live:
                        raise ConanInvalidConfiguration(
                            "Hydra launcher timeout left managed processes before "
                            "harness cleanup: "
                            + ", ".join(
                                f"pid={item[0]} command={item[4]}"
                                for item in live.values()
                            )
                        )
                self._cleanup_processes(process, identities, token, root_identity)
            self._refresh_identities(process, identities, token, root_identity)
            try:
                stdout, stderr = process.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                self._cleanup_processes(process, identities, token, root_identity)
                stdout, stderr = process.communicate(timeout=2)
                timed_out = True

            if timed_out:
                self._assert_zero_residue(
                    identities,
                    process=process,
                    token=token,
                    root_identity=root_identity,
                )
                raise ConanInvalidConfiguration(
                    f"managed MPI command exceeded {outer_timeout} seconds: {command}"
                )
            if stdout.strip():
                self.output.info(stdout.strip())
            if stderr.strip():
                self.output.info(f"MPI stderr: {stderr.strip()}")
            live = {}
            if process.returncode != 0:
                if require_launcher_cleanup:
                    live = self._wait_for_zero_residue(
                        identities,
                        timeout=5,
                        process=process,
                        token=token,
                        root_identity=root_identity,
                    )
                    if live:
                        raise ConanInvalidConfiguration(
                            "Hydra required fallback cleanup after a malformed PMI "
                            "abort: "
                            + ", ".join(
                                f"pid={item[0]} command={item[4]}"
                                for item in live.values()
                            )
                        )
                else:
                    self._cleanup_processes(
                        process, identities, token, root_identity
                    )
            else:
                self._refresh_identities(process, identities, token, root_identity)
                live = self._live_identities(identities)
                if live:
                    self._cleanup_processes(process, identities, token, root_identity)
            self._assert_zero_residue(
                identities,
                process=process,
                token=token,
                root_identity=root_identity,
            )
            if live:
                raise ConanInvalidConfiguration(
                    "MPI command returned while descendants were still alive: "
                    + ", ".join(
                        f"pid={item[0]} command={item[4]}" for item in live.values()
                    )
                )
            return process.returncode, identities, stdout, stderr
        except BaseException as error:
            if process is not None:
                try:
                    self._cleanup_processes(process, identities, token, root_identity)
                except BaseException as cleanup_error:
                    self._attach_cleanup_failure(error, cleanup_error)
            raise

    def _run_case(
        self,
        package_folder,
        executable,
        launcher="mpiexec",
        launcher_args="",
        ranks=2,
        executable_args=(),
        extra_environment=None,
        mpi_timeout="60",
        outer_timeout=70,
        ignore_errors=False,
        require_launcher_cleanup=False,
        observation_gate=None,
    ):
        launcher_path = self._path(launcher, package_folder)
        command = [launcher_path]
        command.extend(split(launcher_args))
        command.extend(["-n", str(ranks), os.path.join(self.build_folder, executable)])
        command.extend(executable_args)
        poison, marker = self._poison_environment(
            f"run-{os.path.basename(package_folder)}-{executable}"
        )
        extras = Environment()
        for name, value in (extra_environment or {}).items():
            extras.define(name, value)
        with poison.vars(self).apply():
            with self._closed_environment(package_folder, timeout=mpi_timeout):
                with extras.vars(self).apply():
                    self._assert_overrides_cleared()
                    result = self._run_managed_mpi(
                        command,
                        outer_timeout,
                        require_launcher_cleanup=require_launcher_cleanup,
                        observation_gate=observation_gate,
                    )
        if os.path.exists(marker):
            raise ConanInvalidConfiguration(
                f"closed MPI runtime environment invoked poison marker {marker}"
            )
        if result[0] != 0 and not ignore_errors:
            raise ConanInvalidConfiguration(
                f"MPI command failed with {result[0]}: {command}"
            )
        return result

    @staticmethod
    def _file_signature(path):
        with open(path, "rb") as stream:
            digest = hashlib.sha256(stream.read()).hexdigest()
        link_target = os.readlink(path) if os.path.islink(path) else None
        return os.path.getsize(path), digest, link_target

    def _original_snapshot(self, paths):
        return {
            os.path.relpath(path, self._dep().package_folder): self._file_signature(
                path
            )
            for path in paths
        }

    def _assert_original_snapshot(self, paths, expected):
        actual = self._original_snapshot(paths)
        if actual != expected:
            raise ConanInvalidConfiguration(
                "negative relocation test modified the original MPICH package"
            )

    def _expect_missing_proxy_failure(self, relocated):
        original_proxy = self._path("hydra_pmi_proxy", self._dep().package_folder)
        original = self._original_snapshot((original_proxy,))
        proxy = self._path("hydra_pmi_proxy", relocated)
        hidden = f"{proxy}.negative-hidden"
        os.replace(proxy, hidden)
        try:
            result = self._run_case(
                relocated,
                "test_mpi_c_relocated",
                ignore_errors=True,
            )
            if result[0] == 0:
                raise ConanInvalidConfiguration(
                    "relocated mpiexec succeeded without hydra_pmi_proxy"
                )
        finally:
            os.replace(hidden, proxy)
        self._assert_original_snapshot((original_proxy,), original)
        self._run_case(
            relocated,
            "test_mpi_c_relocated",
        )

    def _expect_missing_libmpi_failure(self, relocated):
        original_libs = sorted(
            path
            for path in glob.glob(
                os.path.join(self._dep().package_folder, "lib", "libmpi.so*")
            )
            if os.path.isfile(path)
        )
        relocated_libs = sorted(
            path
            for path in glob.glob(os.path.join(relocated, "lib", "libmpi.so*"))
            if os.path.isfile(path)
        )
        if not original_libs or not relocated_libs:
            raise ConanInvalidConfiguration(
                "MPICH relocation negative test requires libmpi.so artifacts"
            )

        original = self._original_snapshot(original_libs)
        hidden = []
        try:
            for path in relocated_libs:
                hidden_path = f"{path}.negative-hidden"
                os.replace(path, hidden_path)
                hidden.append((path, hidden_path))
            result = self._run_case(
                relocated,
                "test_mpi_c_relocated",
                ignore_errors=True,
            )
            if result[0] == 0:
                raise ConanInvalidConfiguration(
                    "relocated MPI consumer succeeded without libmpi.so artifacts"
                )
        finally:
            for path, hidden_path in reversed(hidden):
                os.replace(hidden_path, path)
        self._assert_original_snapshot(original_libs, original)
        self._run_case(
            relocated,
            "test_mpi_c_relocated",
        )

    def _expect_missing_libpmi_failure(self, relocated):
        original_libs = sorted(
            path
            for path in glob.glob(
                os.path.join(self._dep().package_folder, "lib", "libpmi.so*")
            )
            if os.path.isfile(path)
        )
        relocated_libs = sorted(
            path
            for path in glob.glob(os.path.join(relocated, "lib", "libpmi.so*"))
            if os.path.isfile(path)
        )
        if not original_libs or not relocated_libs:
            raise ConanInvalidConfiguration(
                "MPICH relocation negative test requires libpmi.so artifacts"
            )

        original = self._original_snapshot(original_libs)
        hidden = []
        try:
            for path in relocated_libs:
                hidden_path = f"{path}.negative-hidden"
                os.replace(path, hidden_path)
                hidden.append((path, hidden_path))
            result = self._run_case(
                relocated,
                "test_mpi_c_relocated",
                ignore_errors=True,
            )
            if result[0] == 0:
                raise ConanInvalidConfiguration(
                    "relocated MPI consumer succeeded without libpmi.so artifacts"
                )
        finally:
            for path, hidden_path in reversed(hidden):
                os.replace(hidden_path, path)
        self._assert_original_snapshot(original_libs, original)
        self._run_case(
            relocated,
            "test_mpi_c_relocated",
        )

    def _expect_one_rank_failure(self, package_folder, executable):
        result = self._run_case(
            package_folder,
            executable,
            ranks=1,
            ignore_errors=True,
        )
        if result[0] == 0:
            raise ConanInvalidConfiguration(
                f"two-rank consumer accepted a one-rank launch: {executable}"
            )
        self._run_case(package_folder, executable)

    def _assert_failed_process_evidence(
        self, label, pid_file, result, expected_ranks=2, expected_proxies=1
    ):
        if result[0] == 0:
            raise ConanInvalidConfiguration(
                f"controlled MPI {label} probe unexpectedly succeeded"
            )
        try:
            with open(pid_file, "r", encoding="utf-8") as stream:
                recorded = {
                    int(line.strip()) for line in stream if line.strip().isdigit()
                }
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"cannot read controlled MPI {label} PID evidence: {error}"
            ) from error
        if len(recorded) != expected_ranks:
            raise ConanInvalidConfiguration(
                f"controlled MPI {label} probe recorded {len(recorded)} ranks"
            )
        observed = result[1]
        if not recorded.issubset(observed):
            raise ConanInvalidConfiguration(
                f"controlled MPI {label} ranks were not bound to the launcher tree"
            )
        proxy_count = sum(
            identity[4] == "hydra_pmi_proxy" for identity in observed.values()
        )
        if proxy_count < expected_proxies:
            raise ConanInvalidConfiguration(
                f"controlled MPI {label} probe observed {proxy_count} Hydra proxies"
            )
        self._assert_zero_residue(observed)
        return observed

    @staticmethod
    def _load_role_rank_records(path, label):
        pattern = re.compile(r"^role=(parent|spawned) rank=(\d+) pid=(\d+) pgid=(-?\d+)$")
        records = {}
        try:
            with open(path, "r", encoding="utf-8") as stream:
                for number, raw_line in enumerate(stream, start=1):
                    line = raw_line.strip()
                    if not line:
                        continue
                    match = pattern.fullmatch(line)
                    if match is None:
                        raise ConanInvalidConfiguration(
                            f"{label} evidence line {number} is malformed: {line!r}"
                        )
                    key = (match.group(1), int(match.group(2)))
                    if key in records:
                        raise ConanInvalidConfiguration(
                            f"{label} recorded duplicate role/rank evidence for {key}"
                        )
                    records[key] = (int(match.group(3)), int(match.group(4)))
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"cannot read {label} evidence {path}: {error}"
            ) from error
        return records

    def _assert_recorded_process_roles(
        self, label, pid_file, result, expected_roles, expected_proxies
    ):
        observed = result[1]
        expected = tuple(expected_roles)
        records = self._load_role_rank_records(pid_file, label)
        if result[0] == 0:
            raise ConanInvalidConfiguration(
                f"controlled MPI {label} probe unexpectedly succeeded"
            )
        if tuple(sorted(records)) != tuple(sorted(expected)):
            raise ConanInvalidConfiguration(
                f"controlled MPI {label} recorded roles {sorted(records)} "
                f"instead of {sorted(expected)}"
            )
        for role_rank, identity in records.items():
            pid, recorded_process_group = identity
            observed_identity = observed.get(pid)
            if observed_identity is None:
                raise ConanInvalidConfiguration(
                    f"controlled MPI {label} PID {pid} was not bound to the launcher tree"
                )
            if observed_identity[2] != recorded_process_group:
                raise ConanInvalidConfiguration(
                    f"controlled MPI {label} PID {pid} changed process group from "
                    f"{recorded_process_group} to {observed_identity[2]}"
                )
        proxy_count = sum(
            identity[4] == "hydra_pmi_proxy" for identity in observed.values()
        )
        if proxy_count != expected_proxies:
            raise ConanInvalidConfiguration(
                f"controlled MPI {label} probe observed {proxy_count} Hydra proxies"
            )
        self._assert_zero_residue(observed)
        return records, observed

    def _assert_role_rank_canary(self, label, canary_file, expected_records):
        recorded = self._load_role_rank_records(canary_file, label)
        if recorded != expected_records:
            raise ConanInvalidConfiguration(
                f"{label} canary evidence changed: expected {expected_records}, "
                f"got {recorded}"
            )

    def _expect_process_failure(
        self, package_folder, executable, mode, launcher_args=""
    ):
        pid_file = os.path.join(
            self.build_folder,
            f"process-control-{os.path.basename(package_folder)}-{mode}.pids",
        )
        if os.path.lexists(pid_file):
            os.unlink(pid_file)
        result = self._run_case(
            package_folder,
            executable,
            launcher_args=launcher_args,
            executable_args=(mode,),
            extra_environment={"CODEX_MPI_PID_FILE": pid_file},
            mpi_timeout="2" if mode == "timeout" else "60",
            outer_timeout=15,
            ignore_errors=True,
            require_launcher_cleanup=True,
        )
        self._assert_failed_process_evidence(mode, pid_file, result)
        self._run_case(
            package_folder,
            "test_mpi_c"
            if package_folder == self._dep().package_folder
            else "test_mpi_c_relocated",
        )

    def _expect_malformed_pmi_abort(self, package_folder, mode):
        label = f"malformed-{mode}"
        pid_file = os.path.join(self.build_folder, f"{label}.pids")
        canary = os.path.join(self.build_folder, f"{label}.canary")
        armed_file = os.path.join(self.build_folder, f"{label}.armed")
        release_file = os.path.join(self.build_folder, f"{label}.observer-release")
        release_token = secrets.token_hex(32)
        for path in (pid_file, canary, armed_file, release_file):
            if os.path.lexists(path):
                os.unlink(path)
        result = self._run_case(
            package_folder,
            "test_pmi_malformed_abort",
            launcher_args="-disable-auto-cleanup",
            executable_args=(mode,),
            extra_environment={
                "CODEX_MPI_PID_FILE": pid_file,
                "CODEX_MPI_MALFORMED_CANARY": canary,
                "CODEX_MPI_FRAME_ARMED_FILE": armed_file,
                "CODEX_MPI_OBSERVER_RELEASE_FILE": release_file,
                "CODEX_MPI_OBSERVER_RELEASE_TOKEN": release_token,
            },
            outer_timeout=15,
            ignore_errors=True,
            require_launcher_cleanup=True,
            observation_gate={
                "pid_file": pid_file,
                "release_file": release_file,
                "token": release_token,
                "expected_roles": (
                    ("parent", 0),
                    ("parent", 1),
                    ("spawned", 0),
                ),
                "expected_proxies": 1,
            },
        )
        self._assert_observation_gate_file(release_file, release_token)
        expected_records, _observed = self._assert_recorded_process_roles(
            label,
            pid_file,
            result,
            expected_roles=(("parent", 0), ("parent", 1), ("spawned", 0)),
            expected_proxies=1,
        )
        try:
            with open(armed_file, "r", encoding="utf-8") as stream:
                armed = stream.read()
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"cannot read malformed PMI armed evidence for {mode}: {error}"
            ) from error
        if armed != f"{mode}\n":
            raise ConanInvalidConfiguration(
                f"malformed PMI armed evidence changed for {mode}: {armed!r}"
            )
        time.sleep(4.5)
        if os.path.exists(canary):
            raise ConanInvalidConfiguration(
                f"malformed PMI abort left a delayed rank canary for {mode}"
            )
        self._run_case(package_folder, "test_mpi_c")

    def _expect_valid_pmi_abort(self, package_folder, mode):
        label = f"valid-{mode}"
        pid_file = os.path.join(self.build_folder, f"{label}.pids")
        canary = os.path.join(self.build_folder, f"{label}.canary")
        armed_file = os.path.join(self.build_folder, f"{label}.armed")
        release_file = os.path.join(self.build_folder, f"{label}.observer-release")
        release_token = secrets.token_hex(32)
        for path in (pid_file, canary, armed_file, release_file):
            if os.path.lexists(path):
                os.unlink(path)
        result = self._run_case(
            package_folder,
            "test_pmi_malformed_abort",
            launcher_args="-disable-auto-cleanup",
            executable_args=(mode,),
            extra_environment={
                "CODEX_MPI_PID_FILE": pid_file,
                "CODEX_MPI_VALID_CANARY": canary,
                "CODEX_MPI_FRAME_ARMED_FILE": armed_file,
                "CODEX_MPI_OBSERVER_RELEASE_FILE": release_file,
                "CODEX_MPI_OBSERVER_RELEASE_TOKEN": release_token,
            },
            outer_timeout=15,
            ignore_errors=True,
            require_launcher_cleanup=True,
            observation_gate={
                "pid_file": pid_file,
                "release_file": release_file,
                "token": release_token,
                "expected_roles": (
                    ("parent", 0),
                    ("parent", 1),
                    ("spawned", 0),
                ),
                "expected_proxies": 1,
            },
        )
        self._assert_observation_gate_file(release_file, release_token)
        self._assert_recorded_process_roles(
            label,
            pid_file,
            result,
            expected_roles=(("parent", 0), ("parent", 1), ("spawned", 0)),
            expected_proxies=1,
        )
        if "unable to parse PMI command" in result[3]:
            raise ConanInvalidConfiguration(
                f"valid PMI abort control was rejected by the PMI parser for {mode}"
            )
        try:
            with open(armed_file, "r", encoding="utf-8") as stream:
                armed = stream.read()
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"cannot read valid PMI armed evidence for {mode}: {error}"
            ) from error
        if armed != f"{mode}\n":
            raise ConanInvalidConfiguration(
                f"valid PMI armed evidence changed for {mode}: {armed!r}"
            )
        if os.path.lexists(canary):
            raise ConanInvalidConfiguration(
                f"valid PMI abort survived long enough to write a canary for {mode}"
            )
        self._run_case(package_folder, "test_mpi_c")

    def _expect_detached_descendant_cleanup(self, package_folder, mode):
        outer_timeout = 15
        identity = f"{os.path.basename(package_folder)}-{mode}"
        rank_pid_file = os.path.join(
            self.build_folder, f"process-control-{identity}.pids"
        )
        escape_pid_file = os.path.join(
            self.build_folder, f"process-control-{identity}.escape-pid"
        )
        canary = os.path.join(self.build_folder, f"process-control-{identity}.canary")
        armed_file = os.path.join(
            self.build_folder, f"process-control-{identity}.escape-armed"
        )
        release_file = os.path.join(
            self.build_folder, f"process-control-{identity}.escape-release"
        )
        release_token = secrets.token_hex(32)
        for path in (rank_pid_file, escape_pid_file, canary, armed_file, release_file):
            if os.path.lexists(path):
                os.unlink(path)
        environment = {
            "CODEX_MPI_PID_FILE": rank_pid_file,
            "CODEX_MPI_ESCAPE_PID_FILE": escape_pid_file,
            "CODEX_MPI_ESCAPE_CANARY": canary,
            "CODEX_MPI_ESCAPE_ARMED_FILE": armed_file,
            "CODEX_MPI_ESCAPE_RELEASE_FILE": release_file,
            "CODEX_MPI_ESCAPE_RELEASE_TOKEN": release_token,
        }
        try:
            self._run_case(
                package_folder,
                "test_process_control",
                executable_args=(mode,),
                extra_environment=environment,
                outer_timeout=outer_timeout,
            )
        except ConanInvalidConfiguration as error:
            message = str(error)
            returned_with_live_descendant = (
                "returned while descendants were still alive" in message
            )
            timeout_prefix = (
                f"managed MPI command exceeded {outer_timeout} seconds: "
            )
            timed_out_command = None
            if message.startswith(timeout_prefix):
                try:
                    timed_out_command = ast.literal_eval(message[len(timeout_prefix) :])
                except (SyntaxError, ValueError):
                    timed_out_command = None
            timed_out_with_bound_probe = (
                isinstance(timed_out_command, list)
                and len(timed_out_command) >= 2
                and str(timed_out_command[-2]).replace("\\", "/").rsplit("/", 1)[-1]
                == "test_process_control"
                and timed_out_command[-1] == mode
            )
            if not (returned_with_live_descendant or timed_out_with_bound_probe):
                raise
        else:
            raise ConanInvalidConfiguration(
                f"managed MPI runner accepted detached descendant mode {mode}"
            )

        try:
            with open(armed_file, "r", encoding="ascii") as stream:
                armed = stream.read()
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"cannot read detached MPI cleanup gate evidence for {mode}: {error}"
            ) from error
        if armed != f"{release_token}\n":
            raise ConanInvalidConfiguration(
                f"detached MPI cleanup gate evidence changed for {mode}"
            )
        try:
            with open(escape_pid_file, "r", encoding="utf-8") as stream:
                values = [line.strip() for line in stream if line.strip()]
            escape_pid = int(values[0]) if len(values) == 1 else -1
        except (OSError, ValueError) as error:
            raise ConanInvalidConfiguration(
                f"cannot read detached MPI descendant evidence for {mode}: {error}"
            ) from error
        if escape_pid <= 0 or self._process_identity(escape_pid) is not None:
            raise ConanInvalidConfiguration(
                f"detached MPI descendant survived cleanup for {mode}: {escape_pid}"
            )
        if os.path.lexists(canary):
            raise ConanInvalidConfiguration(
                f"detached MPI descendant wrote canary before cleanup gate for {mode}"
            )
        try:
            with open(release_file, "x", encoding="ascii", newline="\n") as stream:
                stream.write(f"{release_token}\n")
                stream.flush()
                os.fsync(stream.fileno())
            with open(release_file, "r", encoding="ascii") as stream:
                release = stream.read()
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"cannot publish detached MPI cleanup gate for {mode}: {error}"
            ) from error
        if release != f"{release_token}\n":
            raise ConanInvalidConfiguration(
                f"detached MPI cleanup gate readback changed for {mode}"
            )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if os.path.lexists(canary):
                raise ConanInvalidConfiguration(
                    f"detached MPI descendant survived cleanup gate for {mode}"
                )
            time.sleep(0.05)
        if os.path.lexists(canary):
            raise ConanInvalidConfiguration(
                f"detached MPI descendant survived cleanup gate for {mode}"
            )
        self._run_case(package_folder, "test_mpi_c")

    def test(self):
        self._prepare_tmp()
        package = self._dep().package_folder
        self._validate_license_contract(package)
        for name in self._wrapper_names + self._launcher_names:
            self._path(name, package)
        required_libraries = (
            os.path.join(package, "lib", "libmpi.so"),
            os.path.join(package, "lib", "libmpifort.so"),
        )
        missing = [path for path in required_libraries if not os.path.isfile(path)]
        if missing:
            raise ConanInvalidConfiguration(
                "MPICH test package is missing required libraries: "
                + ", ".join(missing)
            )
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "mpich/5.0.1.2 requires native two-rank OHOS execution"
            )

        cases = (
            ("test_mpi_c", "mpiexec"),
            ("test_mpi_cxx", "mpiexec"),
            ("test_mpi_cpp_alias", "mpirun"),
            ("test_mpifh", "mpiexec"),
            ("test_use_mpi", "mpiexec"),
            ("test_mixed", "mpiexec"),
            ("test_nwchem_mpif4_bridge", "mpiexec"),
        )
        for executable, launcher in cases:
            self._run_case(
                package,
                executable,
                launcher=launcher,
            )
        for executable in ("cmake_mpi_c", "cmake_mpi_fortran"):
            self._run_case(package, executable)

        relocated = os.path.join(self.build_folder, "relocated-mpich")
        for executable, launcher in cases:
            self._run_case(
                relocated,
                f"{executable}_relocated",
                launcher=launcher,
            )
        for executable in ("cmake_mpi_c", "cmake_mpi_fortran"):
            self._run_case(relocated, f"{executable}_relocated")
        self._expect_one_rank_failure(package, "test_mpi_c")
        self._expect_one_rank_failure(relocated, "test_mpi_c_relocated")
        self._expect_process_failure(package, "test_process_control", "abort")
        self._expect_process_failure(
            relocated,
            "test_process_control_relocated",
            "timeout",
            launcher_args="-disable-auto-cleanup",
        )
        for mode in (
            "missing",
            "nonnumeric",
            "empty",
            "overflow",
            "trailing-junk",
            "above-int",
            "below-int",
            "leading-tab",
            "leading-cr",
            "leading-vt",
            "leading-ff",
        ):
            self._expect_malformed_pmi_abort(package, mode)
        for mode in ("valid-int-max", "valid-int-min"):
            self._expect_valid_pmi_abort(package, mode)
        self._expect_detached_descendant_cleanup(package, "detach")
        self._expect_detached_descendant_cleanup(package, "detach-kill")
        self._expect_missing_proxy_failure(relocated)
        self._expect_missing_libmpi_failure(relocated)
        self._expect_missing_libpmi_failure(relocated)
