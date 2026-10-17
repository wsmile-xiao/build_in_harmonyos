#!/usr/bin/env python3
"""Conan recipe for MPICH 5.0.1.2 with C and LLVM Flang bindings."""

import errno
import glob
import hashlib
import json
import os
import re
import secrets
import signal
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from shlex import quote, split

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    get,
    load,
    rm,
    rmdir,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MpichConan(ConanFile):
    name = "mpich"
    version = "5.0.1.2"
    description = "Portable implementation of the Message Passing Interface (MPI)"
    license = "mpich2 AND (Apache-2.0 WITH LLVM-exception)"
    homepage = "https://www.mpich.org/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    _flang_reference = "flang-ohos/20.1.0"
    _llvm_license_name = "LLVM-LICENSE.TXT"
    _llvm_license_sha256 = (
        "8d85c1057d742e597985c7d4e6320b015a9139385cff4cbae06ffc0ebe89afee"
    )
    _runtime_archives = (
        "libFortranRuntime.a",
        "libFortranDecimal.a",
        "libFortranCommon.a",
    )
    _release_f90_names = ("mpi.f90",)
    _generated_f90_names = (
        "mpi_base.f90",
        "pmpi_base.f90",
        "mpi_constants.f90",
        "mpi_sizeofs.f90",
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
    _target_env = "/system/bin/env"
    _target_test_shell = "/system/bin/sh"
    _upstream_run_token_name = "MPICH_UPSTREAM_RUN_TOKEN"
    _upstream_raw_completed = 2858
    _upstream_logical_completed = 1410
    _upstream_junit_skipped = 31
    _upstream_junit_only_skipped = 30
    _upstream_inventory_sha256 = (
        "d577e6ee61f8034c3801104cae0f0a994e4e84d62312c019240541bf8a023359"
    )
    _upstream_junit_inventory_sha256 = (
        "98e4731ab254e5ab59eade24e6b7de9fd842bcbae422687a4abde0e8befaf054"
    )
    _upstream_skips = {
        ("./impls/mpich/threads/pt2pt", "multinic_infohints", "", "2"),
    }
    _upstream_environment_overrides = (
        "BASH_ENV",
        "CC",
        "CFLAGS",
        "CMAKE_PREFIX_PATH",
        "CMAKE_TOOLCHAIN_FILE",
        "CONFIG_SITE",
        "CPATH",
        "CPP",
        "CPPFLAGS",
        "CPLUS_INCLUDE_PATH",
        "CXX",
        "CXXFLAGS",
        "C_INCLUDE_PATH",
        "ENV",
        "FC",
        "FCFLAGS",
        "FC_INCLUDE_PATH",
        "FFLAGS",
        "FPATH",
        "F77",
        "F90",
        "F90FLAGS",
        "HOME",
        "HYDRA_BINDING",
        "HYDRA_BOOTSTRAP",
        "HYDRA_BOOTSTRAP_EXEC",
        "HYDRA_CONFIG_FILE",
        "HYDRA_LAUNCHER",
        "HYDRA_LAUNCHER_AUTOFORK",
        "HYDRA_LAUNCHER_EXEC",
        "HYDRA_LAUNCHER_EXTRA_ARGS",
        "HYDRA_LAUNCHER_SSH_LIMIT",
        "HYDRA_LAUNCHER_SSH_LIMIT_TIME",
        "HYDRA_MAPPING",
        "HYDRA_MEMBIND",
        "HYDRA_PROXY_RETRY_COUNT",
        "HYDRA_RMK",
        "HYDRA_TOPOLIB",
        "HYDRA_USE_DDD",
        "HYDRA_USE_STRACE",
        "HYDRA_USE_VALGRIND",
        "I_MPI_CC",
        "I_MPI_CXX",
        "I_MPI_F77",
        "I_MPI_F90",
        "I_MPI_FC",
        "I_MPI_ROOT",
        "LD_AUDIT",
        "LD_DEBUG",
        "LD_LIBRARY_PATH",
        "LD_PRELOAD",
        "LD_PROFILE",
        "LIBRARY_PATH",
        "LDFLAGS",
        "MAKEFILES",
        "MAKEFLAGS",
        "MFLAGS",
        "MPICC",
        "MPICC_PROFILE",
        "MPICPP",
        "MPICXX",
        "MPICXX_PROFILE",
        "MPIEXEC",
        "MPIEXEC_EXECUTABLE",
        "MPIEXEC_MAX_NUMPROCS",
        "MPIEXEC_NUMPROC_FLAG",
        "MPIEXEC_POSTFLAGS",
        "MPIEXEC_PREFLAGS",
        "MPIEXEC_TIMEOUT",
        "MPIF77",
        "MPIF77_PROFILE",
        "MPIF90",
        "MPIF90_PROFILE",
        "MPIFC",
        "MPIFORT",
        "MPIFORT_PROFILE",
        "MPIRUN",
        "MPITEST_RUN_INDIVIDUAL",
        "MPITEST_TIMEOUT",
        "MPITEST_TIMEOUT_MULTIPLIER",
        "MPIR_CVAR_ALLREDUCE_INTRA_ALGORITHM",
        "MPIR_CVAR_PMI_VERSION",
        "MPIR_PARAM_CH3_PORT_RANGE",
        "PMIX_NAMESPACE",
        "PMI_SUBVERSION",
        "PMI_VERSION",
        "MPICH_CC",
        "MPICH_CC_OLD",
        "MPICH_CXX",
        "MPICH_CXX_OLD",
        "MPICH_F77",
        "MPICH_F77_OLD",
        "MPICH_F90",
        "MPICH_F90_OLD",
        "MPICH_FC",
        "MPICH_FC_OLD",
        "MPICH_HOME",
        "MPICH_ROOT",
        "MPI_HOME",
        "MPI_ROOT",
        "NLSPATH",
        "OBJC_INCLUDE_PATH",
        "OMPI_CC",
        "OMPI_CXX",
        "OMPI_F77",
        "OMPI_FC",
        "OPAL_PREFIX",
        "PKG_CONFIG_LIBDIR",
        "PKG_CONFIG_PATH",
        "PERL5LIB",
        "ZDOTDIR",
    )
    _hydra_abort_disabled_cleanup_return = (
        "    if (HYD_server_info.user_global.auto_cleanup == 0) {\n"
        "        HYDU_FUNC_EXIT();\n"
        "        return HYD_SUCCESS;\n"
        "    }\n"
    )
    _hydra_abort_unconditional_cleanup = (
        "    HYDU_ASSERT(!pmi_errno, status);\n"
        "\n"
        "  fn_cleanup:\n"
        "    status = HYD_pmiserv_abort_cleanup(&exitcode);\n"
    )
    _hydra_abort_exitcode = "    int exitcode = EXIT_FAILURE;\n"
    _hydra_abort_exitcode_validation = (
        '    exitcode_text = PMIU_cmd_find_keyval(pmi, "exitcode");\n'
        "    if (exitcode_text == NULL) {\n"
        "        if (pmi->version == PMIU_WIRE_V1)\n"
        "            goto fn_cleanup;\n"
        "    } else {\n"
        "        digits = exitcode_text;\n"
        "        if (*digits == '+' || *digits == '-')\n"
        "            digits++;\n"
        "        if (!is_ascii_digit(*digits))\n"
        "            goto fn_cleanup;\n"
        "        while (*digits != '\\0') {\n"
        "            if (!is_ascii_digit(*digits))\n"
        "                goto fn_cleanup;\n"
        "            digits++;\n"
        "        }\n"
        "        errno = 0;\n"
        "        parsed_exitcode = strtol(exitcode_text, &endptr, 10);\n"
        "        if (errno == ERANGE || endptr == exitcode_text || *endptr != '\\0' ||\n"
        "            parsed_exitcode < INT_MIN || parsed_exitcode > INT_MAX)\n"
        "            goto fn_cleanup;\n"
        "    }\n"
    )
    _hydra_abort_cleanup_label = "  fn_cleanup:\n"
    _hydra_abort_cleanup_function = (
        "HYD_status HYD_pmiserv_abort_cleanup(int *exitcode)\n"
        "{\n"
        "    HYD_status status = HYD_SUCCESS;\n"
        "    HYD_status overall_status = HYD_SUCCESS;\n"
    )
    _hydra_pg_registry_comment = (
        "    /* hydra_server.h declares these process-group accessors; pg.c implements them. */\n"
    )
    _hydra_pg_max_id_declaration = "int PMISERV_pg_max_id(void);\n"
    _hydra_pg_max_id_definition = "int PMISERV_pg_max_id(void)\n"
    _hydra_abort_cleanup_signal = (
        "            if (proxy->control_fd == HYD_FD_UNSET || proxy->control_fd == HYD_FD_CLOSED)\n"
        "                continue;\n"
        "            status = HYD_pmcd_pmiserv_send_signal(proxy, SIGKILL);\n"
        "            if (status != HYD_SUCCESS) {\n"
        "                overall_status = status;\n"
        "                *exitcode = EXIT_FAILURE;\n"
        "            }\n"
        "        }\n"
    )
    _hydra_abort_cleanup = (
        "    status = HYDT_bsci_wait_for_completion(0);\n"
        "    if (status != HYD_SUCCESS) {\n"
        "        overall_status = status;\n"
        "        *exitcode = EXIT_FAILURE;\n"
        "    }\n"
        "    return overall_status;\n"
        "}\n"
    )
    _hydra_abort_cleanup_call = (
        "    status = HYD_pmiserv_abort_cleanup(&exitcode);\n"
    )
    _hydra_abort_cleanup_exit = (
        "    exit(exitcode);\n"
    )
    _hydra_abort_fail_cleanup = "  fn_fail:\n    goto fn_cleanup;\n"
    _hydra_abort_cleanup_declaration = (
        "HYD_status HYD_pmiserv_abort_cleanup(int *exitcode);\n"
    )
    _hydra_abort_parse_failure_cleanup = (
        "    if (status != HYD_SUCCESS && pmi_version == PMIU_WIRE_V1 &&\n"
        "        is_malformed_abort_pmi1(buf, buflen)) {\n"
        "        int exitcode = EXIT_FAILURE;\n"
        "        status = HYD_pmiserv_abort_cleanup(&exitcode);\n"
        "        exit(exitcode);\n"
        "    }\n"
    )
    _hydra_abort_malformed_boundary = (
        "    return (unsigned char) buf[sizeof(prefix) - 1] <= 0x20;\n"
    )
    _upstream_wrapper_timeout = 60
    _upstream_case_timeout = 180
    _upstream_test_timeout = 7200
    _upstream_environ_einval_timeout = 0.25
    _upstream_environ_einval_interval = 0.01

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "mpich/5.0.1.2 is validated only for os=OHOS, arch=armv8"
            )
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "mpich/5.0.1.2 publishes one validated shared C/Fortran ABI"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("perl/5.42.2")
        self.tool_requires(self._flang_reference, package_id_mode="full_mode")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        llvm_license = self.conan_data["licenses"]["llvm"]
        if llvm_license.get("sha256") != self._llvm_license_sha256:
            raise ConanInvalidConfiguration(
                "LLVM license input does not match the frozen 20.1.0 digest"
            )
        download(
            self,
            url=llvm_license["url"],
            filename=os.path.join(self.source_folder, self._llvm_license_name),
            sha256=llvm_license["sha256"],
        )

    def _config_shell(self):
        configured = os.environ.get("CONFIG_SHELL")
        if configured and os.path.isfile(configured) and os.access(configured, os.X_OK):
            return configured
        return shutil.which("bash") or shutil.which("sh") or "/system/bin/sh"

    def _compiler_candidate(self, key, fallback):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        configured = compilers.get(key)
        candidate = configured
        if not (candidate and os.path.isfile(candidate)):
            candidate = shutil.which(fallback) or configured or fallback
        return candidate

    def _compiler_executable(self, key, fallback):
        return self._shell_wrapped(self._compiler_candidate(key, fallback))

    def _tool_executable(self, *names):
        for name in names:
            candidate = shutil.which(name)
            if candidate:
                return self._shell_wrapped(candidate)
        return names[-1]

    def _shell_wrapped(self, candidate):
        if candidate and os.path.isfile(candidate):
            with open(candidate, "r", encoding="utf-8", errors="ignore") as wrapper:
                first_line = wrapper.readline()
            if first_line.startswith("#!") and "/bin/sh" in first_line:
                return f"{self._config_shell()} {candidate}"
        return candidate

    def _flang_inputs(self):
        package = self.dependencies.build["flang-ohos"].package_folder
        compiler = os.path.join(package, "bin", "flang")
        library_dir = os.path.join(package, "lib")
        required = [compiler]
        required.extend(
            os.path.join(library_dir, name) for name in self._runtime_archives
        )
        missing = [path for path in required if not os.path.isfile(path)]
        if missing:
            raise ConanInvalidConfiguration(
                "flang-ohos/20.1.0 is missing required inputs: {}".format(
                    ", ".join(missing)
                )
            )
        return package, compiler, library_dir

    def _flang_driver_command(self, flang):
        cc = self._compiler_candidate("c", "clang")
        command = [cc, "-print-resource-dir"]
        if self._shell_wrapped(cc) != cc:
            command.insert(0, self._config_shell())
        try:
            resource_dir = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ConanInvalidConfiguration(
                "cannot query the OHOS Clang resource directory"
            ) from exc

        if not os.path.isabs(resource_dir):
            raise ConanInvalidConfiguration(
                f"invalid OHOS Clang resource directory: {resource_dir}"
            )
        llvm_root = os.path.abspath(os.path.join(resource_dir, "..", "..", ".."))
        native_root = os.path.dirname(llvm_root)
        sysroot = os.path.join(native_root, "sysroot")
        llvm_bin = os.path.join(llvm_root, "bin")
        target_lib = os.path.join(llvm_root, "lib", "aarch64-linux-ohos")
        required = (
            os.path.join(sysroot, "usr", "lib", "aarch64-linux-ohos", "Scrt1.o"),
            os.path.join(
                resource_dir,
                "lib",
                "aarch64-linux-ohos",
                "libclang_rt.builtins.a",
            ),
            os.path.join(target_lib, "libunwind.a"),
            os.path.join(llvm_bin, "ld.lld"),
        )
        missing = [path for path in required if not os.path.isfile(path)]
        if missing:
            raise ConanInvalidConfiguration(
                "OHOS Clang SDK is missing required Flang link inputs: {}".format(
                    ", ".join(missing)
                )
            )

        args = (
            flang,
            "--target=aarch64-linux-ohos",
            f"--sysroot={sysroot}",
            "-resource-dir",
            resource_dir,
            "-B",
            llvm_bin,
            f"-L{target_lib}",
        )
        return " ".join(quote(arg) for arg in args)

    def _relax_autoconf_tmp_permissions(self):
        shell = self._config_shell()
        for root, _, files in os.walk(self.source_folder):
            for filename in files:
                path = os.path.join(root, filename)
                with open(path, "r", encoding="utf-8", errors="ignore") as script:
                    content = script.read()
                relaxed = content
                if filename == "configure":
                    relaxed = relaxed.replace("umask 077", "umask 002")
                first_line, separator, rest = relaxed.partition("\n")
                if first_line.startswith("#!") and "/bin/sh" in first_line:
                    relaxed = f"#!{shell}{separator}{rest}"
                if relaxed != content:
                    with open(path, "w", encoding="utf-8") as script:
                        script.write(relaxed)

    def _validate_autotools_triplets(self):
        shell = self._config_shell()
        scripts = {"config.guess": [], "config.sub": []}
        for root, _, files in os.walk(self.source_folder):
            for filename in scripts:
                if filename in files:
                    scripts[filename].append(os.path.join(root, filename))

        for filename, paths in scripts.items():
            if len(paths) != 18:
                raise ConanInvalidConfiguration(
                    f"expected 18 MPICH {filename} copies, found {len(paths)}"
                )
            for path in paths:
                try:
                    subprocess.run(
                        [shell, "-n", path],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                except (OSError, subprocess.CalledProcessError) as exc:
                    raise ConanInvalidConfiguration(
                        f"invalid shell syntax in {path}"
                    ) from exc

        for path in scripts["config.guess"]:
            output = subprocess.run(
                [shell, path],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            if output != "aarch64-unknown-linux-ohos":
                raise ConanInvalidConfiguration(
                    f"{path} returned an invalid native triplet: {output}"
                )

        matrix = (
            ("aarch64-linux-ohos", "aarch64-unknown-linux-ohos"),
            ("aarch64-unknown-linux-ohos", "aarch64-unknown-linux-ohos"),
            ("x86_64-pc-linux-gnu", "x86_64-pc-linux-gnu"),
        )
        for path in scripts["config.sub"]:
            for argument, expected in matrix:
                output = subprocess.run(
                    [shell, path, argument],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
                if output != expected:
                    raise ConanInvalidConfiguration(
                        f"{path} normalized {argument} as {output}, expected {expected}"
                    )

    def _configure_args(self):
        return [
            "--prefix=/",
            "--enable-fortran",
            "--enable-f77",
            "--enable-f90",
            "--disable-f08",
            "--disable-cxx",
            "--enable-romio",
            "--with-device=ch3:sock",
            "--with-pm=hydra",
            "--with-pmi=pmi1",
            "--with-pmilib=install",
            "--with-hwloc=no",
            "--with-wrapper-dl-type=none",
            "--with-datatype-engine=dataloop",
            "--enable-fast=all",
            "--enable-g=none",
            "--enable-shared",
            "--disable-static",
            f"CONFIG_SHELL={self._config_shell()}",
        ]

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(self._configure_args())
        toolchain.generate()

    def _native_environment(self):
        flang_package, flang, flang_lib = self._flang_inputs()
        flang_command = self._flang_driver_command(flang)
        shell = self._config_shell()
        noop = self._tool_executable("true")
        python = self._python3_command()
        cc = self._compiler_executable("c", "clang")
        cxx = self._compiler_executable("cpp", "clang++")
        values = {
            "SHELL": shell,
            "CONFIG_SHELL": shell,
            "CONFIG_RPATH_SHELL": shell,
            # Bind generation to the interpreter already executing Conan;
            # never search PATH or import from a user site directory.
            "PYTHON": python,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONHOME": "",
            "PYTHONNOUSERSITE": "1",
            "PYTHONPATH": "",
            # MPICH persists CPPFLAGS in every compiler wrapper. Keep the
            # Worker's user-local include path out of the published package.
            "CPPFLAGS": "-DNDEBUG",
            # The declaration is present, but the target sandbox rejects the
            # underlying syscall. Keep ROMIO on its portable non-setfsuid path.
            "ac_cv_func_setfsuid": "no",
            "CC": cc,
            "CXX": cxx,
            "FC": flang_command,
            "F77": flang_command,
            "AR": self._tool_executable("llvm-ar", "ar"),
            "RANLIB": self._tool_executable("llvm-ranlib", "ranlib"),
            "NM": self._tool_executable("llvm-nm", "nm"),
            "LD": self._tool_executable("ld.lld", "lld", "ld"),
            "LDFLAGS": f"-L{flang_lib}",
            "MKDIR_P": "/system/bin/mkdir -p",
            "AUTORECONF": noop,
            "ACLOCAL": noop,
            "AUTOCONF": noop,
            "AUTOHEADER": noop,
            "AUTOMAKE": noop,
        }
        runtime_path = os.pathsep.join(
            path for path in (flang_lib, os.environ.get("LD_LIBRARY_PATH")) if path
        )
        values["LD_LIBRARY_PATH"] = runtime_path
        return flang_package, values

    @staticmethod
    def _snapshot_regular_files(root, names, label):
        snapshot = {}
        for name in names:
            path = os.path.join(root, name)
            if os.path.islink(path) or not os.path.isfile(path):
                raise ConanInvalidConfiguration(f"{label} is missing {name}")
            with open(path, "rb") as stream:
                content = stream.read()
            if not content:
                raise ConanInvalidConfiguration(f"{label} contains empty {name}")
            snapshot[name] = hashlib.sha256(content).hexdigest()
        return snapshot

    @staticmethod
    def _python3_command():
        executable = os.path.realpath(sys.executable)
        if (
            sys.version_info.major != 3
            or not os.path.isabs(executable)
            or not os.path.isfile(executable)
            or any(character.isspace() for character in executable)
        ):
            raise ConanInvalidConfiguration(
                "Conan must run under an executable Python 3 path without whitespace"
            )
        probe = subprocess.run(
            [executable, "-B", "-s", "-c", "import sys; print(sys.version_info[0])"],
            check=False,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONHASHSEED": "0",
                "PYTHONHOME": "",
                "PYTHONNOUSERSITE": "1",
                "PYTHONPATH": "",
            },
        )
        if probe.returncode != 0 or probe.stdout.strip() != "3" or probe.stderr:
            raise ConanInvalidConfiguration(
                "Conan Python cannot execute the isolated MPICH F90 generator"
            )
        return f"{executable} -B -s"

    def _release_f90_snapshot(self):
        root = os.path.join(self.source_folder, "src", "binding", "fortran", "use_mpi")
        if os.path.islink(root) or not os.path.isdir(root):
            raise ConanInvalidConfiguration("MPICH release F90 source is missing")
        discovered = sorted(
            filename
            for filename in os.listdir(root)
            if filename.endswith(".f90")
        )
        if discovered != list(self._release_f90_names):
            raise ConanInvalidConfiguration(
                "unexpected MPICH release F90 source inventory: "
                + ", ".join(discovered)
            )
        return self._snapshot_regular_files(
            root, self._release_f90_names, "MPICH release F90 source"
        )

    def _generated_f90_snapshot(self, require_exact=False):
        build_root = os.path.join(
            self.build_folder, "src", "binding", "fortran", "use_mpi"
        )
        if require_exact:
            discovered = sorted(
                filename
                for filename in os.listdir(build_root)
                if filename.endswith(".f90")
            )
            if discovered != sorted(self._generated_f90_names):
                raise ConanInvalidConfiguration(
                    "unexpected configure-generated MPICH F90 inventory: "
                    + ", ".join(discovered)
                )
        return self._snapshot_regular_files(
            build_root, self._generated_f90_names, "generated MPICH F90 binding"
        )

    def _validate_generated_f90(self, source_before, python, generated_before=None):
        if self._release_f90_snapshot() != source_before:
            raise ConanInvalidConfiguration(
                "configure or make changed the official MPICH F90 source"
            )
        generated = self._generated_f90_snapshot(
            require_exact=generated_before is None
        )
        if generated_before is not None and generated != generated_before:
            raise ConanInvalidConfiguration(
                "make changed the configure-generated MPICH F90 bindings"
            )
        if generated_before is None:
            config_log = load(self, os.path.join(self.build_folder, "config.log"))
            config_status = load(self, os.path.join(self.build_folder, "config.status"))
            generator = os.path.join(self.source_folder, "maint", "gen_binding_f90.py")
            command = (
                f'cmd_gen_binding_f90="{python} {generator} '
                '-f-logical-size=4 -ignore-tkr=dir"'
            )
            if config_status.count(command) != 1:
                raise ConanInvalidConfiguration(
                    "configure did not bind the exact MPICH F90 generator command"
                )
            if "Use pre-generated Fortran mpi binding." in config_log:
                raise ConanInvalidConfiguration(
                    "configure bypassed the bound MPICH F90 generator"
                )
        return generated

    @classmethod
    def _ordered_fragments_present(cls, content, fragments):
        return all(content.count(fragment) == 1 for fragment in fragments) and [
            content.index(fragment) for fragment in fragments
        ] == sorted(content.index(fragment) for fragment in fragments)

    @classmethod
    def _hydra_abort_cleanup_contract_is_valid(
        cls, misc_content, cb_content, header_content
    ):
        return (
            cls._hydra_abort_disabled_cleanup_return not in misc_content
            and cls._ordered_fragments_present(
                misc_content,
                (
                    cls._hydra_abort_exitcode,
                    cls._hydra_abort_exitcode_validation,
                    cls._hydra_abort_unconditional_cleanup,
                    cls._hydra_abort_cleanup_label,
                    cls._hydra_abort_cleanup_call,
                    cls._hydra_abort_cleanup_exit,
                    cls._hydra_abort_fail_cleanup,
                ),
            )
            and cls._ordered_fragments_present(
                misc_content,
                (
                    cls._hydra_abort_cleanup_function,
                    cls._hydra_pg_registry_comment,
                    cls._hydra_abort_cleanup_signal,
                    cls._hydra_abort_cleanup,
                ),
            )
            and cls._hydra_abort_cleanup_declaration in header_content
            and cls._hydra_abort_parse_failure_cleanup in cb_content
            and cls._hydra_abort_malformed_boundary in cb_content
        )

    def _validate_hydra_abort_cleanup_contract(self):
        misc_path = os.path.join(
            self.source_folder,
            "src",
            "pm",
            "hydra",
            "mpiexec",
            "pmiserv_misc.c",
        )
        cb_path = os.path.join(
            self.source_folder,
            "src",
            "pm",
            "hydra",
            "mpiexec",
            "pmiserv_cb.c",
        )
        header_path = os.path.join(
            self.source_folder,
            "src",
            "pm",
            "hydra",
            "mpiexec",
            "pmiserv_pmi.h",
        )
        misc_content = load(self, misc_path)
        cb_content = load(self, cb_path)
        header_content = load(self, header_path)
        if not self._hydra_abort_cleanup_contract_is_valid(
            misc_content, cb_content, header_content
        ):
            raise ConanInvalidConfiguration(
                "Hydra PMI abort cleanup or strict exitcode validation is incomplete"
            )
        for fragment in (
            self._hydra_abort_exitcode,
            self._hydra_abort_exitcode_validation,
            self._hydra_abort_unconditional_cleanup,
            self._hydra_abort_cleanup_function,
            self._hydra_abort_cleanup_signal,
            self._hydra_abort_cleanup_call,
            self._hydra_abort_cleanup_exit,
            self._hydra_abort_fail_cleanup,
        ):
            mutation = misc_content.replace(fragment, "", 1)
            if self._hydra_abort_cleanup_contract_is_valid(
                mutation, cb_content, header_content
            ):
                raise ConanInvalidConfiguration(
                    "Hydra abort cleanup negative mutation was not rejected"
                )
        disabled_cleanup_mutation = misc_content.replace(
            self._hydra_abort_cleanup_label,
            self._hydra_abort_disabled_cleanup_return
            + "\n"
            + self._hydra_abort_cleanup_label,
            1,
        )
        if self._hydra_abort_cleanup_contract_is_valid(
            disabled_cleanup_mutation, cb_content, header_content
        ):
            raise ConanInvalidConfiguration(
                "Hydra abort cleanup accepted an auto_cleanup=0 early return"
            )
        if self._hydra_abort_cleanup_contract_is_valid(
            misc_content,
            cb_content.replace(self._hydra_abort_parse_failure_cleanup, "", 1),
            header_content,
        ):
            raise ConanInvalidConfiguration(
                "Hydra abort cleanup accepted a missing parse-failure cleanup path"
            )
        if self._hydra_abort_cleanup_contract_is_valid(
            misc_content,
            cb_content.replace(self._hydra_abort_malformed_boundary, "", 1),
            header_content,
        ):
            raise ConanInvalidConfiguration(
                "Hydra abort cleanup accepted a missing malformed-command boundary"
            )
        if self._hydra_abort_cleanup_contract_is_valid(
            misc_content,
            cb_content,
            header_content.replace(self._hydra_abort_cleanup_declaration, "", 1),
        ):
            raise ConanInvalidConfiguration(
                "Hydra abort cleanup accepted a missing cleanup declaration"
            )

    def _validate_hydra_pg_registry_contract(self):
        server_header = load(
            self,
            os.path.join(
                self.source_folder,
                "src",
                "pm",
                "hydra",
                "mpiexec",
                "hydra_server.h",
            ),
        )
        pg_source = load(
            self,
            os.path.join(
                self.source_folder,
                "src",
                "pm",
                "hydra",
                "mpiexec",
                "pg.c",
            ),
        )
        if server_header.count(self._hydra_pg_max_id_declaration) != 1:
            raise ConanInvalidConfiguration(
                "Hydra process-group registry maximum-ID API declaration is missing"
            )
        if pg_source.count(self._hydra_pg_max_id_definition) != 1:
            raise ConanInvalidConfiguration(
                "Hydra process-group registry maximum-ID API definition is missing"
            )

    @staticmethod
    def _command_environment(values):
        return " ".join(f"{name}={quote(value)}" for name, value in values.items())

    @staticmethod
    def _runtests_timeout_xml_fragments():
        original = (
            "                RunTestFailed($test_opt, join('', @inline), $runtime);\n"
            "                $flag_aborted = 1;\n"
            "                last;"
        )
        corrected = (
            "                RunTestFailed($test_opt, join('', @inline), $runtime);\n"
            "                RunPostMsg($test_opt);\n"
            "                $flag_aborted = 1;\n"
            "                last;"
        )
        return original, corrected

    @classmethod
    def _close_runtests_timeout_xml_record(cls, content):
        original, corrected = cls._runtests_timeout_xml_fragments()
        if content.count(original) != 1:
            raise ConanInvalidConfiguration(
                "unexpected MPICH run_mpitests timeout XML path"
            )
        return content.replace(original, corrected, 1)

    @classmethod
    def _validate_runtests_timeout_xml_guard(cls):
        original, corrected = cls._runtests_timeout_xml_fragments()
        baseline = f"prefix\n{original}\nsuffix\n"
        expected = f"prefix\n{corrected}\nsuffix\n"
        if cls._close_runtests_timeout_xml_record(baseline) != expected:
            raise ConanInvalidConfiguration(
                "MPICH run_mpitests timeout XML correction changed"
            )
        mutations = (
            baseline.replace("RunTestFailed", "RunTestPassed", 1),
            baseline + original,
            expected,
        )
        for mutation in mutations:
            try:
                cls._close_runtests_timeout_xml_record(mutation)
            except ConanInvalidConfiguration:
                continue
            raise ConanInvalidConfiguration(
                "MPICH run_mpitests timeout XML negative mutation was accepted"
            )

    @staticmethod
    def _grouped_timeout_source_fragments():
        return (
            "my $mpiexec = get_mpiexec_wrapper($np, {});",
            'print $in "TIMEOUT $test_opt->{_timeout}\\n";',
            '$ENV{"MPIEXEC_TIMEOUT"} = $test_opt->{_timeout};',
            "alarm(timeout);",
        )

    @classmethod
    def _grouped_timeout_source_is_valid(cls, runtests_content, multi_tests_content):
        grouped_launch, per_test_timeout, individual_timeout, alarm_timeout = (
            cls._grouped_timeout_source_fragments()
        )
        return (
            runtests_content.count(grouped_launch) == 1
            and runtests_content.count(per_test_timeout) == 1
            and runtests_content.count(individual_timeout) == 1
            and multi_tests_content.count(alarm_timeout) == 1
        )

    @classmethod
    def _validate_grouped_timeout_source_guard(
        cls, runtests_content, multi_tests_content
    ):
        if not cls._grouped_timeout_source_is_valid(
            runtests_content, multi_tests_content
        ):
            raise ConanInvalidConfiguration(
                "unexpected MPICH grouped per-test timeout contract"
            )

        grouped_launch, per_test_timeout, individual_timeout, alarm_timeout = (
            cls._grouped_timeout_source_fragments()
        )
        mutations = (
            (runtests_content.replace(grouped_launch, "", 1), multi_tests_content),
            (runtests_content.replace(per_test_timeout, "", 1), multi_tests_content),
            (runtests_content.replace(individual_timeout, "", 1), multi_tests_content),
            (runtests_content, multi_tests_content.replace(alarm_timeout, "", 1)),
        )
        for mutated_runtests, mutated_multi_tests in mutations:
            if cls._grouped_timeout_source_is_valid(
                mutated_runtests, mutated_multi_tests
            ):
                raise ConanInvalidConfiguration(
                    "MPICH grouped timeout source mutation was accepted"
                )

    @classmethod
    def _upstream_timeout_environment_is_valid(cls, values):
        return (
            values.get("MPITEST_TIMEOUT") == str(cls._upstream_case_timeout)
            and "MPIEXEC_TIMEOUT" not in values
            and "MPITEST_RUN_INDIVIDUAL" not in values
        )

    @classmethod
    def _validate_upstream_timeout_environment_guard(cls, values):
        if not cls._upstream_timeout_environment_is_valid(values):
            raise ConanInvalidConfiguration(
                "MPICH grouped tests require a per-test timeout without a group timeout"
            )

        baseline = {"MPITEST_TIMEOUT": str(cls._upstream_case_timeout)}
        mutations = (
            {},
            {"MPITEST_TIMEOUT": "0"},
            {**baseline, "MPIEXEC_TIMEOUT": str(cls._upstream_case_timeout)},
            {**baseline, "MPITEST_RUN_INDIVIDUAL": "1"},
        )
        for mutation in mutations:
            if cls._upstream_timeout_environment_is_valid(mutation):
                raise ConanInvalidConfiguration(
                    "MPICH grouped timeout environment mutation was accepted"
                )

    @staticmethod
    def _atomic_rmw_gacc_workload_counts():
        return (
            ("#define OP_COUNT 10\n", 1),
            ("#define AM_BUF_NUM  10\n", 1),
            ("#define SHM_BUF_NUM 10000\n", 1),
            ("#define LOOP_SIZE 15\n", 1),
            ("MPI_Get_accumulate(", 4),
            ("MPI_Win_flush(dest, win);", 4),
            ("errors += test_atomic_rmw_gacc();", 2),
        )

    @classmethod
    def _atomic_rmw_gacc_timeout_contract_is_valid(
        cls, testlist_content, source_content
    ):
        default_entry = "atomic_rmw_gacc 3\n"
        bounded_entry = "atomic_rmw_gacc 3 timeLimit=300\n"
        return (
            testlist_content.count(default_entry) == 0
            and testlist_content.count(bounded_entry) == 1
            and all(
                source_content.count(fragment) == expected
                for fragment, expected in cls._atomic_rmw_gacc_workload_counts()
            )
        )

    @classmethod
    def _validate_atomic_rmw_gacc_timeout_contract(
        cls, testlist_content, source_content
    ):
        if not cls._atomic_rmw_gacc_timeout_contract_is_valid(
            testlist_content, source_content
        ):
            raise ConanInvalidConfiguration(
                "unexpected MPICH atomic_rmw_gacc timeout or workload contract"
            )

        bounded_entry = "atomic_rmw_gacc 3 timeLimit=300\n"
        testlist_mutations = (
            testlist_content.replace(bounded_entry, "", 1),
            testlist_content + bounded_entry,
            testlist_content.replace(bounded_entry, "atomic_rmw_gacc 3\n", 1),
            testlist_content.replace(
                bounded_entry, "atomic_rmw_gacc 3 timeLimit=600\n", 1
            ),
        )
        for mutation in testlist_mutations:
            if cls._atomic_rmw_gacc_timeout_contract_is_valid(
                mutation, source_content
            ):
                raise ConanInvalidConfiguration(
                    "MPICH atomic_rmw_gacc timeout mutation was accepted"
                )

        for fragment, _ in cls._atomic_rmw_gacc_workload_counts():
            mutation = source_content.replace(fragment, "", 1)
            if cls._atomic_rmw_gacc_timeout_contract_is_valid(
                testlist_content, mutation
            ):
                raise ConanInvalidConfiguration(
                    "MPICH atomic_rmw_gacc workload mutation was accepted"
                )

    def _prepare_upstream_test_tree(self, python_command):
        self._validate_runtests_timeout_xml_guard()
        source_tests = os.path.join(self.source_folder, "test", "mpi")
        build_tests = os.path.join(self.build_folder, "test", "mpi")
        if not os.path.isdir(source_tests):
            raise ConanInvalidConfiguration(
                "MPICH release is missing the official test/mpi source tree"
            )
        self._validate_atomic_rmw_gacc_timeout_contract(
            load(self, os.path.join(source_tests, "rma", "testlist.in")),
            load(self, os.path.join(source_tests, "rma", "atomic_rmw_gacc.c")),
        )
        if os.path.lexists(build_tests):
            if os.path.islink(build_tests):
                os.unlink(build_tests)
            else:
                shutil.rmtree(build_tests)
        shutil.copytree(source_tests, build_tests)

        configure = os.path.join(build_tests, "configure")
        configure_content = load(self, configure)
        gentests = '"gentests":C) $srcdir/maint/gentests_dtp.sh'
        if configure_content.count(gentests) != 1:
            raise ConanInvalidConfiguration(
                "unexpected MPICH DTPools test generation command"
            )
        save(
            self,
            configure,
            configure_content.replace(
                gentests,
                '"gentests":C) $SHELL $srcdir/maint/gentests_dtp.sh',
                1,
            ),
        )

        makefile_in = os.path.join(build_tests, "Makefile.in")
        makefile_content = load(self, makefile_in)
        runner = "\t$(top_srcdir)/runtests -srcdir=$(srcdir)"
        if makefile_content.count(runner) != 1:
            raise ConanInvalidConfiguration(
                "unexpected MPICH upstream test runner command"
            )
        save(
            self,
            makefile_in,
            makefile_content.replace(
                runner,
                "\t$(PERL) $(top_srcdir)/runtests -srcdir=$(srcdir)",
                1,
            ),
        )

        runtests = os.path.join(build_tests, "runtests")
        runtests_content = load(self, runtests)
        multi_tests_content = load(
            self, os.path.join(build_tests, "include", "multi_tests.c")
        )
        self._validate_grouped_timeout_source_guard(
            runtests_content, multi_tests_content
        )
        lock_replacements = (
            (
                '$lockfile = "/tmp/runtests-$name.lock";',
                '$lockfile = "$ENV{TMPDIR}/runtests-$name.lock";',
            ),
            (
                '$lockfile="/tmp/runtests-mem.lock";',
                '$lockfile="$ENV{TMPDIR}/runtests-mem.lock";',
            ),
        )
        for old_lock, new_lock in lock_replacements:
            if runtests_content.count(old_lock) != 1:
                raise ConanInvalidConfiguration(
                    "unexpected MPICH upstream test lock path"
                )
            runtests_content = runtests_content.replace(old_lock, new_lock, 1)
        runtests_content = self._close_runtests_timeout_xml_record(runtests_content)
        save(self, runtests, runtests_content)

        self._apply_official_abort_xfails(build_tests, python_command)

    def _apply_official_abort_xfails(self, build_tests, python_command):
        xfail_conf = os.path.join(build_tests, "maint", "jenkins", "xfail.conf")
        set_xfail = os.path.join(build_tests, "maint", "jenkins", "set_xfail.py")
        testlist = os.path.join(build_tests, "errors", "comm", "testlist")
        for path in (xfail_conf, set_xfail, testlist):
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(
                    f"MPICH official abort XFAIL input is missing: {path}"
                )

        rule_patterns = (
            r"\* \* \* \* \*\s+/\^intercomm_abort/\s+"
            r"xfail=ticket0\s+errors/comm/testlist",
            r"\* \* \* \* \*\s+/\^\(inter\|sub\)comm_abort/\s+"
            r"xfail=ticket6634\s+errors/comm/testlist",
        )
        source_rules = load(self, xfail_conf).splitlines()
        selected_rules = []
        for pattern in rule_patterns:
            matches = [line for line in source_rules if re.fullmatch(pattern, line)]
            if len(matches) != 1:
                raise ConanInvalidConfiguration(
                    "MPICH official abort XFAIL rule changed: " + pattern
                )
            selected_rules.append(matches[0])

        filtered_conf = os.path.join(build_tests, "official-abort-xfail.conf")
        save(self, filtered_conf, "\n".join(selected_rules) + "\n")

        expected_reasons = (
            ("subcomm_abort", "ticket6634"),
            ("subcomm_abort2", "ticket6634"),
            ("intercomm_abort", "ticket0"),
        )
        expected_lines = load(self, testlist).splitlines(keepends=True)
        for name, reason in expected_reasons:
            matches = [
                index
                for index, line in enumerate(expected_lines)
                if re.match(rf"^{re.escape(name)}\s", line)
            ]
            if len(matches) != 1 or "xfail=" in expected_lines[matches[0]]:
                raise ConanInvalidConfiguration(
                    f"MPICH official abort test entry changed: {name}"
                )
            index = matches[0]
            line = expected_lines[index]
            body = line.rstrip("\r\n")
            ending = line[len(body) :]
            expected_lines[index] = f"{body} xfail={reason}{ending}"
        expected = "".join(expected_lines)

        clean_python = self._command_environment(
            {
                "PYTHONHOME": "",
                "PYTHONNOUSERSITE": "1",
                "PYTHONPATH": "",
            }
        )
        self.run(
            f"{clean_python} {python_command} {quote(set_xfail)} "
            f"--dir={quote(build_tests)} -j openharmony -c clang -o release "
            f"-m ch3:sock -q openharmony -f {quote(filtered_conf)}",
            env="conanbuild",
        )
        if load(self, testlist) != expected:
            raise ConanInvalidConfiguration(
                "MPICH official abort XFAIL application changed unexpected entries"
            )

    @staticmethod
    def _result_text(node, name, required=True):
        child = node.find(name)
        if child is None:
            if required:
                raise ConanInvalidConfiguration(
                    f"MPICH upstream result is missing {name}"
                )
            return ""
        return child.text or ""

    @staticmethod
    def _canonical_inventory_digest(records):
        payload = []
        for key in sorted(records):
            states = records[key]
            payload.append(
                [
                    list(key),
                    [[state, states[state]] for state in sorted(states)],
                ]
            )
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @classmethod
    def _validate_inventory_digest_guard(cls):
        baseline = {
            ("work", "alpha", "", "2"): {"fail": 0, "pass": 2, "skip": 0},
            ("work", "beta", "", "2"): {"fail": 0, "pass": 1, "skip": 0},
        }
        rebalanced = {
            ("work", "alpha", "", "2"): {"fail": 0, "pass": 1, "skip": 0},
            ("work", "beta", "", "2"): {"fail": 0, "pass": 2, "skip": 0},
        }
        substituted = {
            ("work", "alpha-renamed", "", "2"): {
                "fail": 0,
                "pass": 2,
                "skip": 0,
            },
            ("work", "beta", "", "2"): {"fail": 0, "pass": 1, "skip": 0},
        }
        baseline_digest = cls._canonical_inventory_digest(baseline)
        if baseline_digest in {
            cls._canonical_inventory_digest(rebalanced),
            cls._canonical_inventory_digest(substituted),
        }:
            raise ConanInvalidConfiguration(
                "MPICH upstream inventory digest does not bind key multiplicity"
            )

    @classmethod
    def _parse_upstream_summary(cls, path):
        try:
            with open(path, "rb") as stream:
                content = stream.read().rstrip()
        except (OSError, ET.ParseError) as error:
            raise ConanInvalidConfiguration(
                f"cannot read MPICH upstream XML summary {path}: {error}"
            ) from error
        closing_tag = b"</MPITESTRESULTS>"
        if not content.endswith(closing_tag):
            if not content.endswith(b"</MPITEST>"):
                raise ConanInvalidConfiguration(
                    f"MPICH upstream XML summary is truncated: {path}"
                )
            content += b"\n" + closing_tag
        try:
            root = ET.fromstring(content)
        except ET.ParseError as error:
            raise ConanInvalidConfiguration(
                f"cannot parse MPICH upstream XML summary {path}: {error}"
            ) from error
        if root.tag != "MPITESTRESULTS":
            raise ConanInvalidConfiguration(
                f"unexpected MPICH upstream XML root: {root.tag}"
            )

        records = {}
        raw_passed = 0
        raw_failed = 0
        for result in root.findall("MPITEST"):
            key = (
                cls._result_text(result, "WORKDIR"),
                cls._result_text(result, "NAME"),
                cls._result_text(result, "ARGS", required=False),
                cls._result_text(result, "NP"),
            )
            status = cls._result_text(result, "STATUS", required=False).lower()
            if not status:
                state = "skip"
            elif status in ("pass", "fail"):
                state = status
            else:
                raise ConanInvalidConfiguration(
                    f"unknown MPICH upstream test status {status!r} for {key}"
                )
            counts = records.setdefault(
                key,
                {"fail": 0, "pass": 0, "skip": 0},
            )
            counts[state] += 1
            if state == "skip":
                continue
            if state == "pass":
                raw_passed += 1
            else:
                raw_failed += 1

        logical_failed = {key for key, counts in records.items() if counts["fail"]}
        logical_passed = {
            key
            for key, counts in records.items()
            if counts["pass"] and not counts["fail"]
        }
        skipped = {key for key, counts in records.items() if counts["skip"]}
        return {
            "raw_passed": raw_passed,
            "raw_failed": raw_failed,
            "logical_passed": logical_passed,
            "logical_failed": logical_failed,
            "skipped": skipped,
            "inventory_sha256": cls._canonical_inventory_digest(records),
        }

    @classmethod
    def _parse_upstream_junit(cls, path):
        try:
            root = ET.parse(path).getroot()
        except (OSError, ET.ParseError) as error:
            raise ConanInvalidConfiguration(
                f"cannot parse MPICH upstream JUnit summary {path}: {error}"
            ) from error
        suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
        if not suites:
            raise ConanInvalidConfiguration("MPICH upstream JUnit has no testsuite")

        totals = {name: 0 for name in ("tests", "failures", "errors", "skipped")}
        observed_states = {name: 0 for name in ("pass", "failure", "error", "skipped")}
        records = {}
        testcase_count = 0
        for suite in suites:
            for name in totals:
                try:
                    totals[name] += int(suite.get(name, "0"))
                except ValueError as error:
                    raise ConanInvalidConfiguration(
                        f"invalid MPICH upstream JUnit {name} count"
                    ) from error
            testcases = suite.findall("testcase")
            testcase_count += len(testcases)
            for testcase in testcases:
                stable_attributes = tuple(
                    sorted(
                        (name, value)
                        for name, value in testcase.attrib.items()
                        if name not in ("time", "timestamp")
                    )
                )
                key = (suite.get("name", ""), stable_attributes)
                terminal_states = [
                    child.tag.rsplit("}", 1)[-1]
                    for child in testcase
                    if child.tag.rsplit("}", 1)[-1] in ("failure", "error", "skipped")
                ]
                if len(terminal_states) > 1:
                    raise ConanInvalidConfiguration(
                        f"MPICH JUnit testcase has multiple terminal states: {key}"
                    )
                state = terminal_states[0] if terminal_states else "pass"
                observed_states[state] += 1
                counts = records.setdefault(
                    key,
                    {"error": 0, "failure": 0, "pass": 0, "skipped": 0},
                )
                counts[state] += 1
        totals["testcases"] = testcase_count
        totals["observed_states"] = observed_states
        totals["inventory_sha256"] = cls._canonical_inventory_digest(records)
        return totals

    def _validate_upstream_results(self):
        self._validate_inventory_digest_guard()
        test_root = os.path.join(self.build_folder, "test", "mpi")
        summary = self._parse_upstream_summary(os.path.join(test_root, "summary.xml"))
        junit = self._parse_upstream_junit(os.path.join(test_root, "summary.junit.xml"))
        raw_completed = summary["raw_passed"] + summary["raw_failed"]
        logical_completed = len(summary["logical_passed"]) + len(
            summary["logical_failed"]
        )
        failures = sorted(summary["logical_failed"])

        if raw_completed != self._upstream_raw_completed:
            raise ConanInvalidConfiguration(
                "MPICH upstream raw test closure changed: "
                f"expected {self._upstream_raw_completed}, got {raw_completed}"
            )
        if logical_completed != self._upstream_logical_completed:
            raise ConanInvalidConfiguration(
                "MPICH upstream logical test closure changed: "
                f"expected {self._upstream_logical_completed}, got {logical_completed}"
            )
        if summary["skipped"] != self._upstream_skips:
            raise ConanInvalidConfiguration(
                "MPICH upstream skip set changed: "
                f"expected {sorted(self._upstream_skips)}, "
                f"got {sorted(summary['skipped'])}"
            )
        if summary["raw_failed"] or failures:
            raise ConanInvalidConfiguration(
                "MPICH upstream tests failed: "
                f"raw={summary['raw_failed']}, logical={len(failures)}, "
                f"first={failures[:5]}"
            )

        expected_junit = {
            "tests": self._upstream_raw_completed,
            "failures": 0,
            "errors": 0,
            "skipped": self._upstream_junit_skipped,
            "testcases": self._upstream_raw_completed + self._upstream_junit_skipped,
        }
        observed_junit = {name: junit[name] for name in expected_junit}
        if observed_junit != expected_junit:
            raise ConanInvalidConfiguration(
                f"MPICH upstream JUnit closure changed: expected {expected_junit}, "
                f"got {observed_junit}"
            )
        observed_states = junit["observed_states"]
        if (
            observed_states["pass"] != summary["raw_passed"]
            or observed_states["failure"] + observed_states["error"]
            != summary["raw_failed"]
            or observed_states["skipped"] != self._upstream_junit_skipped
            or observed_states["skipped"] - len(summary["skipped"])
            != self._upstream_junit_only_skipped
        ):
            raise ConanInvalidConfiguration(
                "MPICH XML/JUnit identity states disagree: "
                f"XML pass={summary['raw_passed']} fail={summary['raw_failed']} "
                f"runtime-skip={len(summary['skipped'])}; JUnit={observed_states}"
            )

        digests = (
            (
                "summary.xml",
                self._upstream_inventory_sha256,
                summary["inventory_sha256"],
            ),
            (
                "summary.junit.xml",
                self._upstream_junit_inventory_sha256,
                junit["inventory_sha256"],
            ),
        )
        unlocked = [
            label
            for label, expected, _observed in digests
            if not isinstance(expected, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected) is None
        ]
        if unlocked:
            observed = ", ".join(
                f"{label}={digest}" for label, _expected, digest in digests
            )
            raise ConanInvalidConfiguration(
                "MPICH official upstream inventory digest is not locked for "
                f"{', '.join(unlocked)}; preserve one successful official run and "
                f"set the exact constants; observed {observed}"
            )
        mismatches = [
            f"{label}: expected {expected}, got {observed}"
            for label, expected, observed in digests
            if expected != observed
        ]
        if mismatches:
            raise ConanInvalidConfiguration(
                "MPICH official upstream inventory changed: " + "; ".join(mismatches)
            )
        self.output.info(
            "MPICH upstream tests: "
            f"{logical_completed}/{self._upstream_logical_completed} logical PASS, "
            f"{raw_completed}/{self._upstream_raw_completed} raw PASS, "
            f"{len(summary['skipped'])} XML runtime skipped, "
            f"{junit['skipped']} JUnit skipped, "
            f"inventory={summary['inventory_sha256']}, "
            f"junit-inventory={junit['inventory_sha256']}"
        )

    @staticmethod
    def _unique_directories(paths):
        result = []
        identities = set()
        for path in paths:
            if not path or not os.path.isdir(path):
                continue
            identity = os.path.normcase(os.path.realpath(path))
            if identity in identities:
                continue
            result.append(path)
            identities.add(identity)
        return result

    @staticmethod
    def _command_directories(command):
        directories = []
        for token in split(command):
            if os.path.isabs(token) and os.path.isfile(token):
                directories.append(os.path.dirname(token))
        return directories

    def _required_tool_path(self, name, fixed_candidates=()):
        candidate = None
        if fixed_candidates:
            for fixed in fixed_candidates:
                if (
                    os.path.isabs(fixed)
                    and os.path.isfile(fixed)
                    and os.access(fixed, os.X_OK)
                ):
                    candidate = fixed
                    break
        else:
            with VirtualBuildEnv(self).vars().apply():
                candidate = shutil.which(name)
        if (
            not candidate
            or not os.path.isfile(candidate)
            or not os.access(candidate, os.X_OK)
        ):
            raise ConanInvalidConfiguration(
                f"MPICH upstream tests cannot resolve required tool: {name}"
            )
        return os.path.abspath(candidate)

    @staticmethod
    def _perl_library_paths(perl_package):
        root = os.path.join(perl_package, "lib", "perl5")
        paths = []
        for parent in (root, os.path.join(root, "site_perl")):
            if os.path.isdir(parent):
                paths.append(parent)
            for version in sorted(glob.glob(os.path.join(parent, "[0-9]*"))):
                if not os.path.isdir(version):
                    continue
                paths.append(version)
                paths.extend(
                    path
                    for path in sorted(glob.glob(os.path.join(version, "*-linux-*")))
                    if os.path.isdir(path)
                )
        return tuple(dict.fromkeys(paths))

    def _upstream_test_environment_values(self, prefix, flang_package, values):
        perl_package = self.dependencies.build["perl"].package_folder
        perl = os.path.join(perl_package, "bin", "perl")
        if not os.path.isfile(perl):
            raise ConanInvalidConfiguration(
                "perl/5.42.2 is missing its declared interpreter"
            )
        perl_library_paths = self._perl_library_paths(perl_package)
        strict_module = os.path.join(
            perl_package, "lib", "perl5", "5.42.2", "strict.pm"
        )
        if not perl_library_paths or not os.path.isfile(strict_module):
            raise ConanInvalidConfiguration(
                "perl/5.42.2 is missing its relocatable core library paths"
            )
        tools = {
            "env": self._required_tool_path("env", (self._target_env,)),
            "make": self._required_tool_path("make"),
        }
        tools["perl"] = perl
        path_entries = [
            os.path.join(prefix, "bin"),
            os.path.join(flang_package, "bin"),
        ]
        for name in ("CC", "CXX", "FC", "F77", "AR", "RANLIB", "NM", "LD"):
            path_entries.extend(self._command_directories(values[name]))
        path_entries.append(os.path.dirname(self._target_test_shell))
        path_entries.extend(os.path.dirname(path) for path in tools.values())
        path_entries = self._unique_directories(path_entries)

        library_entries = self._unique_directories(
            (
                os.path.join(prefix, "lib"),
                os.path.join(flang_package, "lib"),
            )
        )
        tmpdir = os.path.join(self.build_folder, "tmp")
        safe_home = os.path.join(self.build_folder, "upstream-safe-home")
        if os.path.lexists(safe_home):
            if os.path.islink(safe_home) or not os.path.isdir(safe_home):
                os.unlink(safe_home)
            else:
                shutil.rmtree(safe_home)
        os.makedirs(safe_home, mode=0o700)
        safe_hydra_config = os.path.join(safe_home, "mpiexec.hydra.conf")
        save(self, safe_hydra_config, "")
        allowed = {
            "CONFIG_RPATH_SHELL": self._target_test_shell,
            "CONFIG_SHELL": self._target_test_shell,
            "HOME": safe_home,
            "HYDRA_CONFIG_FILE": safe_hydra_config,
            "LANG": "C",
            "LC_ALL": "C",
            "LD_LIBRARY_PATH": os.pathsep.join(library_entries),
            "MAKE": tools["make"],
            "MKDIR_P": "/system/bin/mkdir -p",
            # The grouped runner enforces this per test with TIMEOUT + alarm().
            # MPIEXEC_TIMEOUT would instead kill the entire grouped Hydra job.
            "MPITEST_TIMEOUT": str(self._upstream_case_timeout),
            "PATH": os.pathsep.join(path_entries),
            "PERL": tools["perl"],
            "PERL5LIB": os.pathsep.join(perl_library_paths),
            "SHELL": self._target_test_shell,
            "TMPDIR": tmpdir,
            "TMPPREFIX": os.path.join(tmpdir, "sh"),
        }
        for name in ("LOGNAME", "USER"):
            value = os.environ.get(name)
            if value:
                allowed[name] = value
        self._validate_upstream_timeout_environment_guard(allowed)
        return allowed, tools

    def _prepare_upstream_environment_poison(self):
        root = os.path.join(self.build_folder, "upstream-environment-poison")
        if os.path.lexists(root):
            shutil.rmtree(root)
        os.makedirs(root)
        marker = os.path.join(root, "called.log")
        script = os.path.join(root, "poison-command")
        save(
            self,
            script,
            f"#!/system/bin/sh\nprintf '%s\\n' \"$0\" >> {quote(marker)}\nexit 97\n",
        )
        os.chmod(script, 0o755)
        names = set(self._wrapper_names + self._launcher_names)
        names.update(("clang", "clang++", "flang", "make", "perl"))
        for name in names:
            shutil.copy2(script, os.path.join(root, name))
        poison_library = os.path.join(root, "libmpi.so")
        save(self, poison_library, "not an ELF shared object\n")
        save(
            self,
            os.path.join(root, ".mpiexec.hydra.conf"),
            "this-is-not-a-valid-hydra-option\n",
        )
        return root, marker, script, poison_library

    def _upstream_poison_environment(self, root, script, poison_library):
        environment = Environment()
        environment.define(
            "PATH",
            os.pathsep.join((root, os.environ.get("PATH", ""))),
        )
        environment.define(
            "LD_LIBRARY_PATH",
            os.pathsep.join((root, os.environ.get("LD_LIBRARY_PATH", ""))),
        )
        for name in self._upstream_environment_overrides:
            environment.define(name, root if name == "HOME" else script)
        environment.define("LD_PRELOAD", poison_library)
        for name in (
            "CPATH",
            "CPLUS_INCLUDE_PATH",
            "C_INCLUDE_PATH",
            "FC_INCLUDE_PATH",
            "LIBRARY_PATH",
        ):
            environment.define(name, root)
        return environment

    @contextmanager
    def _upstream_launch_scrubber(self):
        saved = dict(os.environ)
        try:
            for name in self._upstream_environment_overrides:
                os.environ.pop(name, None)
            os.environ["PATH"] = os.path.dirname(self._target_test_shell)
            yield
        finally:
            os.environ.clear()
            os.environ.update(saved)

    def _validate_upstream_environment_values(self, prefix, allowed, poison_root):
        leaked = [
            name for name in self._upstream_environment_overrides if name in allowed
        ]
        if set(leaked) != {
            "HOME",
            "HYDRA_CONFIG_FILE",
            "LD_LIBRARY_PATH",
            "MPITEST_TIMEOUT",
            "PERL5LIB",
        }:
            raise ConanInvalidConfiguration(
                "MPICH upstream allowlist contains override variables: "
                + ", ".join(leaked)
            )
        expected_home = os.path.join(self.build_folder, "upstream-safe-home")
        expected_config = os.path.join(expected_home, "mpiexec.hydra.conf")
        if (
            os.path.islink(allowed["HOME"])
            or not os.path.isdir(allowed["HOME"])
            or os.path.realpath(allowed["HOME"]) != os.path.realpath(expected_home)
            or os.path.islink(allowed["HYDRA_CONFIG_FILE"])
            or not os.path.isfile(allowed["HYDRA_CONFIG_FILE"])
            or os.path.realpath(allowed["HYDRA_CONFIG_FILE"])
            != os.path.realpath(expected_config)
            or os.path.getsize(allowed["HYDRA_CONFIG_FILE"]) != 0
        ):
            raise ConanInvalidConfiguration(
                "MPICH upstream Hydra configuration is not the controlled empty file"
            )
        perl_package = self.dependencies.build["perl"].package_folder
        expected_perl5lib = os.pathsep.join(
            self._perl_library_paths(perl_package)
        )
        if (
            not expected_perl5lib
            or allowed.get("PERL5LIB") != expected_perl5lib
            or not os.path.isfile(
                os.path.join(perl_package, "lib", "perl5", "5.42.2", "strict.pm")
            )
            or any(
                os.path.commonpath(
                    (os.path.realpath(entry), os.path.realpath(poison_root))
                )
                == os.path.realpath(poison_root)
                for entry in allowed["PERL5LIB"].split(os.pathsep)
            )
        ):
            raise ConanInvalidConfiguration(
                "MPICH upstream Perl library path is not a controlled relocatable closure"
            )
        path_entries = allowed["PATH"].split(os.pathsep)
        library_entries = allowed["LD_LIBRARY_PATH"].split(os.pathsep)
        if any(
            os.path.commonpath((os.path.realpath(entry), os.path.realpath(poison_root)))
            == os.path.realpath(poison_root)
            for entry in path_entries + library_entries
        ):
            raise ConanInvalidConfiguration(
                "MPICH upstream allowlist retained the poison directory"
            )

        selected_bin = os.path.join(prefix, "bin")
        for name in self._wrapper_names + self._launcher_names:
            resolved = shutil.which(name, path=allowed["PATH"])
            expected = os.path.join(selected_bin, name)
            if not resolved or os.path.realpath(resolved) != os.path.realpath(expected):
                raise ConanInvalidConfiguration(
                    f"MPICH upstream allowlist resolved {name} outside selected prefix: "
                    f"{resolved}"
                )

    @staticmethod
    def _isolated_environment_command(env_tool, allowed, command):
        assignments = " ".join(
            f"{name}={quote(allowed[name])}" for name in sorted(allowed)
        )
        return f"{quote(env_tool)} -i {assignments} {command}"

    @staticmethod
    def _upstream_process_identity(pid):
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

    def _upstream_process_tree(self, root_pid):
        identities = {}
        children = {}
        try:
            entries = os.listdir("/proc")
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"cannot inspect /proc for MPICH upstream process cleanup: {error}"
            ) from error
        for entry in entries:
            if not entry.isdigit():
                continue
            identity = self._upstream_process_identity(int(entry))
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

    def _upstream_process_group(self, process_group):
        selected = {}
        try:
            entries = os.listdir("/proc")
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"cannot inspect /proc for MPICH upstream process group: {error}"
            ) from error
        for entry in entries:
            if not entry.isdigit():
                continue
            identity = self._upstream_process_identity(int(entry))
            if identity is not None and identity[2] == process_group:
                selected[identity[0]] = identity
        return selected

    def _upstream_token_processes(self, token):
        expected = f"{self._upstream_run_token_name}={token}".encode("utf-8")
        selected = {}
        try:
            entries = os.listdir("/proc")
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"cannot inspect /proc for MPICH upstream run token: {error}"
            ) from error
        for entry in entries:
            if not entry.isdigit():
                continue
            pid = int(entry)
            before = self._upstream_process_identity(pid)
            if before is None:
                continue
            fields, after = self._upstream_process_environment(pid, before)
            if (
                after is not None
                and before[0] == after[0]
                and before[3] == after[3]
                and expected in fields
            ):
                selected[pid] = after
        return selected

    def _upstream_process_environment(self, pid, before):
        deadline = time.monotonic() + self._upstream_environ_einval_timeout
        observed = before
        while True:
            try:
                with open(f"/proc/{pid}/environ", "rb") as stream:
                    fields = stream.read().split(b"\0")
            except OSError as error:
                if error.errno in (
                    errno.EACCES,
                    errno.ENOENT,
                    errno.EPERM,
                    errno.ESRCH,
                ):
                    return (), None
                after = self._upstream_process_identity(pid)
                if error.errno != errno.EINVAL:
                    raise ConanInvalidConfiguration(
                        f"cannot inspect environment for process {pid}: {error}"
                    ) from error
                if (
                    after is None
                    or observed[3] != after[3]
                    or after[5] == "Z"
                ):
                    return (), None
                if time.monotonic() >= deadline:
                    raise ConanInvalidConfiguration(
                        f"cannot inspect environment for process {pid}: {error}"
                    ) from error
                observed = after
                time.sleep(self._upstream_environ_einval_interval)
                continue
            after = self._upstream_process_identity(pid)
            if (
                after is None
                or observed[3] != after[3]
                or after[5] == "Z"
            ):
                return (), None
            return fields, after

    @classmethod
    def _upstream_identity_is_live(cls, identity):
        current = cls._upstream_process_identity(identity[0])
        return current is not None and current[3] == identity[3]

    def _live_upstream_identities(self, identities):
        return {
            pid: identity
            for pid, identity in identities.items()
            if self._upstream_identity_is_live(identity)
        }

    @classmethod
    def _upstream_root_owns_group(cls, root_identity):
        if root_identity is None or root_identity[2] != root_identity[0]:
            return False
        current = cls._upstream_process_identity(root_identity[0])
        return (
            current is not None
            and current[2] == root_identity[2]
            and current[3] == root_identity[3]
        )

    @classmethod
    def _signal_upstream_identity(cls, identity, signal_number):
        if not cls._upstream_identity_is_live(identity):
            return
        try:
            os.kill(identity[0], signal_number)
        except OSError as error:
            if error.errno != errno.ESRCH:
                raise ConanInvalidConfiguration(
                    f"cannot signal MPICH upstream pid {identity[0]}: {error}"
                ) from error

    @classmethod
    def _signal_upstream_group(cls, root_identity, signal_number):
        if not cls._upstream_root_owns_group(root_identity):
            return
        try:
            os.killpg(root_identity[2], signal_number)
        except OSError as error:
            if error.errno != errno.ESRCH:
                raise ConanInvalidConfiguration(
                    f"cannot signal MPICH upstream process group "
                    f"{root_identity[2]}: {error}"
                ) from error

    def _refresh_upstream_identities(self, process, identities, token, root_identity):
        owns_group = self._upstream_root_owns_group(root_identity)
        if owns_group:
            identities.update(self._upstream_process_tree(process.pid))
            identities.update(self._upstream_process_group(root_identity[2]))
        identities.update(self._upstream_token_processes(token))
        return identities

    @staticmethod
    def _append_upstream_cleanup_error(errors, label, error):
        message = f"{label}: {type(error).__name__}: {error}"
        if message not in errors:
            errors.append(message)

    def _refresh_upstream_cleanup_identities(
        self, process, identities, token, root_identity, errors
    ):
        owns_group = self._upstream_root_owns_group(root_identity)
        scanners = []
        if owns_group:
            scanners.extend(
                (
                    ("process-tree scan", self._upstream_process_tree, process.pid),
                    (
                        "process-group scan",
                        self._upstream_process_group,
                        root_identity[2],
                    ),
                )
            )
        scanners.append(("run-token scan", self._upstream_token_processes, token))
        for label, scanner, argument in scanners:
            try:
                identities.update(scanner(argument))
            except Exception as error:
                self._append_upstream_cleanup_error(errors, label, error)
        return identities

    def _bind_upstream_launcher_identity(
        self, process, identities, token, initial_identity
    ):
        deadline = time.monotonic() + 0.25
        root_identity = initial_identity
        while True:
            if root_identity is None:
                root_identity = self._upstream_process_identity(process.pid)
            token_processes = self._upstream_token_processes(token)
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
                    "cannot bind MPICH upstream launcher identity"
                )
            time.sleep(0.01)
            root_identity = self._upstream_process_identity(process.pid)

    def _cleanup_upstream_processes(self, process, identities, token, root_identity):
        cleanup_errors = []
        self._refresh_upstream_cleanup_identities(
            process, identities, token, root_identity, cleanup_errors
        )
        try:
            self._signal_upstream_group(root_identity, signal.SIGTERM)
        except Exception as error:
            self._append_upstream_cleanup_error(
                cleanup_errors, "process-group SIGTERM", error
            )
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            self._refresh_upstream_cleanup_identities(
                process, identities, token, root_identity, cleanup_errors
            )
            live = self._live_upstream_identities(identities)
            if not live:
                break
            for identity in live.values():
                try:
                    self._signal_upstream_identity(identity, signal.SIGTERM)
                except Exception as error:
                    self._append_upstream_cleanup_error(
                        cleanup_errors, f"pid {identity[0]} SIGTERM", error
                    )
            time.sleep(0.05)

        self._refresh_upstream_cleanup_identities(
            process, identities, token, root_identity, cleanup_errors
        )
        live = self._live_upstream_identities(identities)
        if live:
            try:
                self._signal_upstream_group(root_identity, signal.SIGKILL)
            except Exception as error:
                self._append_upstream_cleanup_error(
                    cleanup_errors, "process-group SIGKILL", error
                )
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                self._refresh_upstream_cleanup_identities(
                    process, identities, token, root_identity, cleanup_errors
                )
                live = self._live_upstream_identities(identities)
                if not live:
                    break
                for identity in live.values():
                    try:
                        self._signal_upstream_identity(identity, signal.SIGKILL)
                    except Exception as error:
                        self._append_upstream_cleanup_error(
                            cleanup_errors, f"pid {identity[0]} SIGKILL", error
                        )
                time.sleep(0.05)

        if process.poll() is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            except Exception as error:
                self._append_upstream_cleanup_error(
                    cleanup_errors, "launcher SIGKILL", error
                )
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self._append_upstream_cleanup_error(
                cleanup_errors,
                "launcher reap",
                ConanInvalidConfiguration(
                    f"cannot reap MPICH upstream launcher pid {process.pid}"
                ),
            )
        remaining = self._wait_for_zero_upstream_residue(
            process,
            identities,
            token,
            root_identity,
            timeout=5,
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
                "MPICH upstream cleanup did not close cleanly: " + "; ".join(details)
            )

    def _wait_for_zero_upstream_residue(
        self,
        process,
        identities,
        token,
        root_identity,
        timeout=5,
        cleanup_errors=None,
    ):
        deadline = time.monotonic() + timeout
        empty_scans = 0
        while time.monotonic() < deadline:
            if cleanup_errors is None:
                self._refresh_upstream_identities(
                    process, identities, token, root_identity
                )
            else:
                self._refresh_upstream_cleanup_identities(
                    process, identities, token, root_identity, cleanup_errors
                )
            live = self._live_upstream_identities(identities)
            if not live:
                empty_scans += 1
                if empty_scans == 2:
                    return {}
            else:
                empty_scans = 0
            time.sleep(0.05)
        if cleanup_errors is None:
            self._refresh_upstream_identities(process, identities, token, root_identity)
        else:
            self._refresh_upstream_cleanup_identities(
                process, identities, token, root_identity, cleanup_errors
            )
        return self._live_upstream_identities(identities)

    @staticmethod
    def _attach_upstream_cleanup_failure(error, cleanup_error):
        note = f"MPICH upstream process cleanup also failed: {cleanup_error}"
        if hasattr(error, "add_note"):
            error.add_note(note)
        else:
            error.args = (*error.args, note)

    def _run_managed_upstream_command(self, command, label, timeout, env_tool, allowed):
        safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "-", label)
        log_path = os.path.join(self.build_folder, f"upstream-command-{safe_label}.log")
        identities = {}
        timed_out = False
        process = None
        root_identity = None
        token = secrets.token_hex(32)
        marked_allowed = dict(allowed)
        marked_allowed[self._upstream_run_token_name] = token
        isolated_command = self._isolated_environment_command(
            env_tool, marked_allowed, command
        )
        try:
            with open(log_path, "w", encoding="utf-8", newline="\n") as log_stream:
                try:
                    process_environment = os.environ.copy()
                    process_environment[self._upstream_run_token_name] = token
                    process = subprocess.Popen(
                        [self._target_test_shell, "-c", f"exec {isolated_command}"],
                        cwd=self.build_folder,
                        env=process_environment,
                        stdout=log_stream,
                        stderr=subprocess.STDOUT,
                        text=True,
                        start_new_session=True,
                    )
                except OSError as error:
                    raise ConanInvalidConfiguration(
                        f"cannot start MPICH upstream command {label}: {error}"
                    ) from error

                root_identity = self._upstream_process_identity(process.pid)
                try:
                    root_identity = self._bind_upstream_launcher_identity(
                        process, identities, token, root_identity
                    )
                except ConanInvalidConfiguration as error:
                    raise ConanInvalidConfiguration(f"{error} for {label}") from error

                deadline = time.monotonic() + timeout
                next_process_scan = time.monotonic()
                while process.poll() is None:
                    now = time.monotonic()
                    if now >= next_process_scan:
                        self._refresh_upstream_identities(
                            process, identities, token, root_identity
                        )
                        next_process_scan = now + 1
                    if now >= deadline:
                        timed_out = True
                        break
                    time.sleep(0.05)
                self._refresh_upstream_identities(
                    process, identities, token, root_identity
                )
                if timed_out:
                    self._cleanup_upstream_processes(
                        process, identities, token, root_identity
                    )
                else:
                    process.wait()

            self._refresh_upstream_identities(process, identities, token, root_identity)
            live = self._live_upstream_identities(identities)
            if timed_out or process.returncode != 0 or live:
                self._cleanup_upstream_processes(
                    process, identities, token, root_identity
                )
            remaining = self._wait_for_zero_upstream_residue(
                process, identities, token, root_identity
            )
            if remaining:
                raise ConanInvalidConfiguration(
                    "MPICH upstream command left process residue: "
                    + ", ".join(
                        f"pid={item[0]} command={item[4]}"
                        for item in remaining.values()
                    )
                )
            if timed_out:
                raise ConanInvalidConfiguration(
                    f"MPICH upstream command {label} exceeded {timeout} seconds"
                )
            if process.returncode != 0:
                try:
                    with open(
                        log_path, "r", encoding="utf-8", errors="replace"
                    ) as stream:
                        tail = stream.read()[-4000:].strip()
                except OSError:
                    tail = ""
                raise ConanInvalidConfiguration(
                    f"MPICH upstream command {label} failed with "
                    f"{process.returncode}: " + tail
                )
            if live:
                raise ConanInvalidConfiguration(
                    f"MPICH upstream command {label} returned while descendants "
                    "were alive: "
                    + ", ".join(
                        f"pid={item[0]} command={item[4]}" for item in live.values()
                    )
                )
        except BaseException as error:
            if process is not None:
                try:
                    self._cleanup_upstream_processes(
                        process, identities, token, root_identity
                    )
                except BaseException as cleanup_error:
                    self._attach_upstream_cleanup_failure(error, cleanup_error)
            raise

    def _run_upstream_tests(self, prefix, flang_package, values):
        allowed, tools = self._upstream_test_environment_values(
            prefix,
            flang_package,
            values,
        )
        poison_root, marker, poison_script, poison_library = (
            self._prepare_upstream_environment_poison()
        )
        poison = self._upstream_poison_environment(
            poison_root,
            poison_script,
            poison_library,
        )
        self._validate_upstream_environment_values(prefix, allowed, poison_root)

        make_command = self._validate_upstream_test_command(
            f"{quote(tools['make'])} -j1 testing prefix={quote(prefix)} "
            f"MKDIR_P={quote('/system/bin/mkdir -p')} "
            f"SHELL={quote(self._target_test_shell)} "
            f"CONFIG_SHELL={quote(self._target_test_shell)}"
        )
        commands = [
            (
                f"{name}-show",
                f"{quote(os.path.join(prefix, 'bin', name))} -show",
                self._upstream_wrapper_timeout,
            )
            for name in self._wrapper_names
        ]
        commands.append(("make-testing", make_command, self._upstream_test_timeout))

        with poison.vars(self).apply():
            with self._upstream_launch_scrubber():
                remaining = [
                    name
                    for name in self._upstream_environment_overrides
                    if name in os.environ
                ]
                if remaining:
                    raise ConanInvalidConfiguration(
                        "MPICH upstream launch scrubber retained overrides: "
                        + ", ".join(remaining)
                    )
                for label, command, timeout in commands:
                    self._run_managed_upstream_command(
                        command,
                        label,
                        timeout,
                        tools["env"],
                        allowed,
                    )

        if os.path.exists(marker):
            called = load(self, marker).strip()
            raise ConanInvalidConfiguration(
                "MPICH upstream tests invoked poisoned environment commands: " + called
            )

    @classmethod
    def _validate_upstream_test_command(cls, command):
        assignments = {}
        for token in split(command):
            name, separator, value = token.partition("=")
            if separator:
                assignments.setdefault(name, []).append(value)

        forbidden = tuple(
            name for name in ("CC", "CXX", "FC", "F77") if name in assignments
        )
        if forbidden:
            raise ConanInvalidConfiguration(
                "MPICH upstream tests must resolve installed MPI wrappers; "
                f"forbidden make variables: {', '.join(forbidden)}"
            )

        required = {
            "SHELL": cls._target_test_shell,
            "CONFIG_SHELL": cls._target_test_shell,
            "MKDIR_P": "/system/bin/mkdir -p",
        }
        invalid = tuple(
            name
            for name, expected in required.items()
            if assignments.get(name) != [expected]
        )
        if invalid:
            raise ConanInvalidConfiguration(
                "MPICH upstream tests require an exact target shell contract; "
                f"invalid make variables: {', '.join(invalid)}"
            )
        return command

    def _replace_install_symlinks(self):
        command = "ln -f -s"
        makefiles = (
            (os.path.join(self.build_folder, "Makefile"), 11, "MPICH"),
            (
                os.path.join(self.build_folder, "src", "pm", "hydra", "Makefile"),
                2,
                "Hydra",
            ),
        )
        for makefile, expected, component in makefiles:
            content = load(self, makefile)
            if content.count(command) != expected:
                raise ConanInvalidConfiguration(
                    f"unexpected {component} install alias command count"
                )
            save(self, makefile, content.replace(command, "cp -p"))

        test_makefile = os.path.join(self.build_folder, "test", "Makefile")
        test_content = load(self, test_makefile)
        test_rule = "cd mpi && ./autogen.sh && ./configure --with-mpi=${prefix}"
        replacement = (
            "cd mpi && $(SHELL) ./configure --disable-cxx "
            "--disable-dependency-tracking --with-mpi=${prefix} "
            "&& cp -p ../../libtool libtool "
            "&& cp -p ../../libtool dtpools/libtool"
        )
        if test_content.count(test_rule) != 1:
            raise ConanInvalidConfiguration(
                "unexpected MPICH upstream test configure rule"
            )
        save(self, test_makefile, test_content.replace(test_rule, replacement, 1))

    def _wrapper_launcher_path(self):
        return os.path.join(self.build_folder, "mpich-wrapper-launcher")

    def _build_wrapper_launcher(self, cc):
        source = os.path.join(self.build_folder, "mpich-wrapper-launcher.c")
        launcher = self._wrapper_launcher_path()
        save(
            self,
            source,
            r"""#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

extern char *realpath(const char *path, char *resolved_path);

#ifndef PATH_MAX
#define PATH_MAX 4096
#endif

static int resolve_launcher(const char *argv0, char *resolved, size_t size)
{
    char candidate[PATH_MAX];
    char *path_copy;
    char *saveptr = NULL;
    char *entry;
    const char *path;

    if (strchr(argv0, '/') != NULL) {
        return realpath(argv0, resolved) != NULL ? 0 : -1;
    }

    path = getenv("PATH");
    if (path == NULL) {
        errno = ENOENT;
        return -1;
    }
    path_copy = strdup(path);
    if (path_copy == NULL) {
        return -1;
    }
    for (entry = strtok_r(path_copy, ":", &saveptr); entry != NULL;
         entry = strtok_r(NULL, ":", &saveptr)) {
        const char *directory = entry[0] == '\0' ? "." : entry;
        int written = snprintf(candidate, sizeof(candidate), "%s/%s", directory, argv0);
        if (written < 0 || (size_t) written >= sizeof(candidate)) {
            continue;
        }
        if (access(candidate, X_OK) == 0 && realpath(candidate, resolved) != NULL) {
            free(path_copy);
            return 0;
        }
    }
    free(path_copy);
    errno = ENOENT;
    (void) size;
    return -1;
}

int main(int argc, char **argv)
{
    char resolved[PATH_MAX];
    char script[PATH_MAX];
    char *slash;
    const char *basename;
    char **shell_argv;
    int written;
    int index;

    if (argc < 1 || resolve_launcher(argv[0], resolved, sizeof(resolved)) != 0) {
        fprintf(stderr, "cannot resolve MPI wrapper %s: %s\n",
                argc > 0 ? argv[0] : "", strerror(errno));
        return 126;
    }
    slash = strrchr(resolved, '/');
    if (slash == NULL) {
        fprintf(stderr, "invalid MPI wrapper path: %s\n", resolved);
        return 126;
    }
    basename = slash + 1;
    *slash = '\0';
    written = snprintf(script, sizeof(script), "%s/%s.sh", resolved, basename);
    if (written < 0 || (size_t) written >= sizeof(script)) {
        fprintf(stderr, "MPI wrapper script path is too long\n");
        return 126;
    }

    shell_argv = calloc((size_t) argc + 2, sizeof(*shell_argv));
    if (shell_argv == NULL) {
        fprintf(stderr, "cannot allocate MPI wrapper arguments: %s\n", strerror(errno));
        return 126;
    }
    shell_argv[0] = "/system/bin/sh";
    shell_argv[1] = script;
    for (index = 1; index < argc; ++index) {
        shell_argv[index + 1] = argv[index];
    }
    execv(shell_argv[0], shell_argv);
    fprintf(stderr, "cannot execute %s: %s\n", script, strerror(errno));
    free(shell_argv);
    return 126;
}
""",
        )
        self.run(f"{cc} {quote(source)} -O2 -o {quote(launcher)}")
        if not os.path.isfile(launcher):
            raise ConanInvalidConfiguration("failed to build MPI wrapper launcher")

    def _install_wrapper_launcher(self, prefix, name):
        wrapper = os.path.join(prefix, "bin", name)
        script = f"{wrapper}.sh"
        if os.path.lexists(script):
            os.unlink(script)
        os.replace(wrapper, script)
        shutil.copy2(self._wrapper_launcher_path(), wrapper)
        os.chmod(wrapper, 0o755)

    def _rewrite_upstream_test_wrappers(self, prefix):
        old_prefix = (
            "prefix=/\n"
            "exec_prefix=/\n"
            "sysconfdir=//etc\n"
            "includedir=//include\n"
            "libdir=//lib"
        )
        new_prefix = (
            f"prefix={quote(prefix)}\n"
            "exec_prefix=$prefix\n"
            "sysconfdir=$prefix/etc\n"
            "includedir=$prefix/include\n"
            "libdir=$prefix/lib"
        )
        for name in self._wrapper_names:
            wrapper = os.path.join(prefix, "bin", name)
            if not os.path.isfile(wrapper):
                raise ConanInvalidConfiguration(
                    f"upstream test install is missing wrapper: {name}"
                )
            content = load(self, wrapper)
            if old_prefix not in content:
                raise ConanInvalidConfiguration(
                    f"unexpected upstream test prefix block in {name}"
                )
            save(self, wrapper, content.replace(old_prefix, new_prefix, 1))
            self._install_wrapper_launcher(prefix, name)

    def _validate_romio_configure_contract(self):
        romio = os.path.join(self.build_folder, "src", "mpi", "romio")
        config_log = os.path.join(romio, "config.log")
        config_header = os.path.join(romio, "adio", "include", "romioconf.h")
        if not os.path.isfile(config_log) or not os.path.isfile(config_header):
            raise ConanInvalidConfiguration(
                "ROMIO configure outputs are missing from the build tree"
            )
        log_content = load(self, config_log)
        if len(re.findall(r"^ARCH='LINUX'$", log_content, re.MULTILINE)) != 1:
            raise ConanInvalidConfiguration(
                "ROMIO did not select the canonical Linux host family"
            )
        if (
            len(
                re.findall(
                    r"^ac_cv_func_setfsuid=no$", log_content, re.MULTILINE
                )
            )
            != 1
        ):
            raise ConanInvalidConfiguration(
                "ROMIO setfsuid capability cache was not consumed"
            )
        header_content = load(self, config_header)
        if re.search(
            r"^\s*#\s*define\s+HAVE_SETFSUID\b", header_content, re.MULTILINE
        ):
            raise ConanInvalidConfiguration(
                "ROMIO enabled the sandbox-denied setfsuid path"
            )

    def build(self):
        apply_conandata_patches(self)
        self._validate_hydra_abort_cleanup_contract()
        self._validate_hydra_pg_registry_contract()
        self._relax_autoconf_tmp_permissions()
        self._validate_autotools_triplets()
        release_f90_snapshot = self._release_f90_snapshot()

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMPPREFIX"] = os.path.join(tmpdir, "sh")

        flang_package, values = self._native_environment()
        os.environ.update(values)
        command_environment = self._command_environment(values)
        configure = os.path.join(self.source_folder, "configure")
        configure_args = " ".join(quote(arg) for arg in self._configure_args())
        self.run(
            f"{command_environment} {quote(values['CONFIG_SHELL'])} "
            f"{quote(configure)} {configure_args}",
            env="conanbuild",
        )
        self._validate_romio_configure_contract()
        generated_f90_snapshot = self._validate_generated_f90(
            release_f90_snapshot, values["PYTHON"]
        )
        self._replace_install_symlinks()
        make_variables = " ".join(
            f"{name}={quote(values[name])}"
            for name in (
                "SHELL",
                "CONFIG_SHELL",
                "CC",
                "CXX",
                "FC",
                "F77",
                "AR",
                "RANLIB",
                "NM",
                "LD",
                "AUTORECONF",
                "ACLOCAL",
                "AUTOCONF",
                "AUTOHEADER",
                "AUTOMAKE",
            )
        )
        self.run(f"make -j1 {make_variables}", env="conanbuild")
        self._validate_generated_f90(
            release_f90_snapshot, values["PYTHON"], generated_f90_snapshot
        )
        self._build_wrapper_launcher(values["CC"])
        self._prepare_upstream_test_tree(values["PYTHON"])
        upstream_prefix = os.path.join(self.build_folder, "upstream-test-prefix")
        if os.path.lexists(upstream_prefix):
            shutil.rmtree(upstream_prefix)
        self.run(
            f"make -j1 install DESTDIR={quote(upstream_prefix)} {make_variables}",
            env="conanbuild",
        )
        self._rewrite_upstream_test_wrappers(upstream_prefix)
        self._run_upstream_tests(upstream_prefix, flang_package, values)
        self._validate_upstream_results()

    @staticmethod
    def _replace_assignment(content, variable, replacement):
        pattern = re.compile(rf'^{re.escape(variable)}="[^"]*"$', re.MULTILINE)
        content, count = pattern.subn(f'{variable}="{replacement}"', content, count=1)
        if count != 1:
            raise ConanInvalidConfiguration(
                f"cannot locate {variable} assignment in MPICH wrapper"
            )
        return content

    def _rewrite_wrapper(self, name, flang_package):
        wrapper = os.path.join(self.package_folder, "bin", name)
        if not os.path.isfile(wrapper):
            raise ConanInvalidConfiguration(f"missing MPICH wrapper: {name}")

        content = load(self, wrapper)
        old_prefix = (
            "prefix=/\n"
            "exec_prefix=/\n"
            "sysconfdir=//etc\n"
            "includedir=//include\n"
            "libdir=//lib"
        )
        new_prefix = (
            'script_dir=$(dirname "$0")\n'
            'prefix=$(cd "$script_dir/.." && pwd)\n'
            "exec_prefix=$prefix\n"
            "sysconfdir=$prefix/etc\n"
            "includedir=$prefix/include\n"
            "libdir=$prefix/lib"
        )
        if old_prefix not in content:
            raise ConanInvalidConfiguration(
                f"unexpected installation prefix block in {name}"
            )
        content = content.replace(old_prefix, new_prefix, 1)
        content = re.sub(r"^#!\s+.*$", "#!/data/service/hnp/bin/bash", content, count=1)

        if name == "mpicc":
            content = self._replace_assignment(content, "CC", "clang")
        elif name in ("mpicxx", "mpic++"):
            content = self._replace_assignment(content, "CXX", "clang++")
        else:
            compiler_block = (
                "clang_resource_dir=$(clang -print-resource-dir) || exit 1\n"
                'llvm_root=$(cd "$(dirname "$clang_resource_dir")/../.." && pwd) '
                "|| exit 1\n"
                'native_root=$(cd "$llvm_root/.." && pwd) || exit 1\n'
                'FC="flang --target=aarch64-linux-ohos '
                "--sysroot=${native_root}/sysroot "
                "-resource-dir ${clang_resource_dir} -B ${llvm_root}/bin "
                '-L${llvm_root}/lib/aarch64-linux-ohos"'
            )
            content, count = re.subn(
                r'^FC="[^"]*"$',
                compiler_block,
                content,
                count=1,
                flags=re.MULTILINE,
            )
            if count != 1:
                raise ConanInvalidConfiguration(
                    f"cannot locate FC assignment in {name}"
                )
            content, count = re.subn(
                r"^modincdir=.*$",
                "modincdir=$includedir",
                content,
                count=1,
                flags=re.MULTILINE,
            )
            if count != 1:
                raise ConanInvalidConfiguration(
                    f"cannot locate module include directory in {name}"
                )
            runtime_flags = " ".join(
                "${{libdir}}/flang-runtime/{}".format(archive)
                for archive in self._runtime_archives
            )
            marker = 'final_libs="@MPICH_MPIFORT_LIBS@"'
            if marker in content:
                raise ConanInvalidConfiguration(
                    f"unexpanded configure variable remains in {name}"
                )
            match = re.search(r'^final_libs="([^"]*)"$', content, re.MULTILINE)
            if not match:
                raise ConanInvalidConfiguration(
                    f"cannot locate Fortran runtime flags in {name}"
                )
            content = (
                content[: match.end()]
                + f'\nfinal_libs="${{final_libs}} {runtime_flags} -lm"'
                + content[match.end() :]
            )

        for spelling in {
            flang_package,
            os.path.realpath(flang_package),
            flang_package.replace("\\", "/"),
        }:
            if spelling:
                content = content.replace(spelling, "${libdir}/flang-runtime")

        pmi_archive = os.path.join(
            self.build_folder, "src", "pmi", "libpmi.la"
        )
        pmi_spellings = {
            pmi_archive,
            os.path.realpath(pmi_archive),
            pmi_archive.replace("\\", "/"),
        }
        pmi_patterns = tuple(
            re.compile(
                rf"(?<![\\A-Za-z0-9_./+:\-]){re.escape(spelling)}"
                r"(?![\\A-Za-z0-9_./+:\-])"
            )
            for spelling in pmi_spellings
            if spelling
        )
        pmi_occurrences = sum(
            len(pattern.findall(content)) for pattern in pmi_patterns
        )
        if pmi_occurrences != 1:
            raise ConanInvalidConfiguration(
                f"expected one build-tree libpmi archive in {name}, "
                f"got {pmi_occurrences}"
            )
        for pattern in pmi_patterns:
            content = pattern.sub("-lpmi", content)

        forbidden = (
            self.source_folder,
            self.build_folder,
            self.package_folder,
            ".conan2",
            "/storage/Users/currentUser/usr/local",
        )
        leaks = [value for value in forbidden if value and value in content]
        if leaks:
            raise ConanInvalidConfiguration(
                f"{name} contains non-relocatable paths: {', '.join(leaks)}"
            )
        save(self, wrapper, content)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        mpich_licenses = copy(
            self,
            "COPYRIGHT",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        llvm_licenses = copy(
            self,
            self._llvm_license_name,
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        license_counts = (len(mpich_licenses), len(llvm_licenses))
        if license_counts != (1, 1):
            raise ConanInvalidConfiguration(
                "incomplete license package: expected MPICH COPYRIGHT and "
                f"LLVM-LICENSE.TXT; got {license_counts}"
            )

        flang_package, _flang, flang_lib = self._flang_inputs()
        runtime_dir = os.path.join(self.package_folder, "lib", "flang-runtime")
        for archive in self._runtime_archives:
            copy(self, archive, src=flang_lib, dst=runtime_dir, keep_path=False)

        rewritten = set()
        for wrapper in self._wrapper_names:
            wrapper_path = os.path.join(self.package_folder, "bin", wrapper)
            target = os.path.realpath(wrapper_path)
            if target in rewritten:
                continue
            self._rewrite_wrapper(wrapper, flang_package)
            self._install_wrapper_launcher(self.package_folder, wrapper)
            rewritten.add(target)

        for pattern in ("*.la", "*.dylib"):
            rm(self, pattern, folder=os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share"))

        required = [
            os.path.join("bin", name)
            for name in self._wrapper_names + self._launcher_names
        ]
        required.extend(
            os.path.join("bin", f"{name}.sh") for name in self._wrapper_names
        )
        required.extend(
            os.path.join("include", name) for name in ("mpi.h", "mpif.h", "mpi.mod")
        )
        required.extend(
            os.path.join("lib", name) for name in ("libmpi.so", "libmpifort.so")
        )
        required.extend(
            os.path.join("lib", "flang-runtime", name)
            for name in self._runtime_archives
        )
        required.extend(
            os.path.join("licenses", name)
            for name in ("COPYRIGHT", self._llvm_license_name)
        )
        missing = [
            relative
            for relative in required
            if not os.path.isfile(os.path.join(self.package_folder, relative))
        ]
        if missing:
            raise ConanInvalidConfiguration(
                "MPICH package is missing required C/Fortran artifacts: {}".format(
                    ", ".join(missing)
                )
            )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "MPICH")
        self.cpp_info.bindirs = ["bin"]

        c_component = self.cpp_info.components["c"]
        c_component.libs = ["mpi"]
        c_component.system_libs = ["m", "pthread", "dl"]
        c_component.set_property("cmake_target_name", "MPI::MPI_C")
        c_component.set_property("pkg_config_name", "mpich")

        fortran_component = self.cpp_info.components["fortran"]
        fortran_component.libs = [
            "mpifort",
            "FortranRuntime",
            "FortranDecimal",
            "FortranCommon",
        ]
        fortran_component.libdirs = ["lib", "lib/flang-runtime"]
        fortran_component.requires = ["c"]
        fortran_component.system_libs = ["m"]
        fortran_component.set_property("cmake_target_name", "MPI::MPI_Fortran")
        fortran_component.set_property("pkg_config_name", "mpich-fortran")

        bindir = os.path.join(self.package_folder, "bin")
        libdir = os.path.join(self.package_folder, "lib")
        self.runenv_info.prepend_path("PATH", bindir)
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", libdir)
        self.buildenv_info.prepend_path("PATH", bindir)
        for variable, executable in (
            ("MPICC", "mpicc"),
            ("MPICXX", "mpicxx"),
            ("MPIF77", "mpif77"),
            ("MPIF90", "mpif90"),
            ("MPIFORT", "mpifort"),
            ("MPIEXEC", "mpiexec"),
        ):
            self.buildenv_info.define_path(variable, os.path.join(bindir, executable))
