#!/usr/bin/env python3
import glob
import os
import shutil
import uuid

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SocketWrapperConan(ConanFile):
    name = "socket-wrapper"
    version = "1.5.2"
    description = "A library passing all BSD sockets API calls through a Unix socket"
    license = "BSD-3-Clause"
    homepage = "https://gitlab.com/cwrap/socket_wrapper"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True],
        "with_upstream_tests": [True, False],
    }
    default_options = {
        "shared": True,
        "with_upstream_tests": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "socket-wrapper requires POSIX socket APIs and LD_PRELOAD support"
            )
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "socket-wrapper builds shared interposition libraries only"
            )

    def build_requirements(self):
        if self.options.with_upstream_tests:
            self.test_requires(self.conan_data["requirements"]["cmocka"])

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        if self.options.with_upstream_tests:
            deps = CMakeDeps(self)
            deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["UNIT_TESTING"] = bool(self.options.with_upstream_tests)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        if str(self.settings.os) == "OHOS":
            # cmake does not know the host "HarmonyOS" platform and then
            # drops the -Wl,-soname flag for versioned shared libraries;
            # declare OHOS explicitly so libsocket_wrapper.so keeps its
            # DT_SONAME (L5a) and the versioned file layout.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "OHOS"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            # Cross-compile standard: skip the try-compile EXE link step
            # (it invokes lld, which fails on CI workers whose
            # libxml2.so.16 resolution is broken — see PR #7709 CI
            # #36816/#36847). We only build shared libraries + test
            # executables via the project's own rules, which link through
            # clang's driver and are unaffected.
            tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
            # With EXE try-compile disabled, ConfigureChecks.cmake's
            # check_* results are unreliable. Pin every probe to the
            # authoritative values for OHOS musl (verified against the
            # sysroot libc.so symbol table with llvm-nm) so generated
            # config.h matches what the compiler actually declares.
            _musl_yes = {
                "HAVE_STRNCPY", "HAVE_VSNPRINTF", "HAVE_SNPRINTF",
                "HAVE_SIGNALFD", "HAVE_EVENTFD", "HAVE_TIMERFD_CREATE",
                "HAVE_ACCEPT4", "HAVE_RECVMMSG", "HAVE_SENDMMSG",
                "HAVE_SYSCALL", "HAVE_DLOPEN", "HAVE_GETADDRINFO",
            }
            _musl_no = {
                # libc symbols absent on musl (llvm-nm verified)
                "HAVE_BINDRESVPORT", "HAVE_GETPROGNAME", "HAVE_GETEXECNAME",
                "HAVE_PLEDGE", "HAVE_FCNTL64",
                # LFS64: symbols exist as aliases but the headers define
                # them as macros — patch 0001 undef's them, so the config
                # must agree (else redefinition, see CI #36816 round 1)
                "HAVE_OPEN64", "HAVE_OPENAT64", "HAVE_FOPEN64",
                # Solaris branch (CMake does not know "OHOS" → NOT LINUX)
                "HAVE_LIBNSL", "HAVE_LIBSOCKET",
                # Windows/Darwin prefixed variants (llvm-nm verified absent)
                "HAVE__SOCKET", "HAVE__CLOSE", "HAVE___CLOSE_NOCANCEL",
                # glibc-only program-name globals (musl lacks both)
                "HAVE_PROGRAM_INVOCATION_SHORT_NAME",
            }
            for var in _musl_yes:
                tc.cache_variables[var] = True
            for var in _musl_no:
                tc.cache_variables[var] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.with_upstream_tests:
            if str(self.settings.os) == "OHOS":
                self._sign_upstream_test_artifacts()
            test_runtime_dir = self._upstream_test_runtime_dir()
            os.makedirs(test_runtime_dir, exist_ok=True)
            test_env = Environment()
            test_env.define("TMPDIR", test_runtime_dir)
            # The OHOS/musl loader does not search the directory of the
            # executable, so help test_fork_thread_deadlock find its
            # build-tree libthread_deadlock.so neighbor.
            test_env.append_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, "tests")
            )
            with test_env.vars(self).apply():
                self.run("ctest -N", cwd=self.build_folder)
                self.run("ctest --output-on-failure --verbose -j1", cwd=self.build_folder)

    def _upstream_test_runtime_dir(self):
        """Pick a short TMPDIR for the upstream suite.

        socket_wrapper stores the AF_UNIX socket files inside
        SOCKET_WRAPPER_DIR and the kernel limits sun_path to ~108 bytes.
        Deep Conan build folders on OHOS easily exceed that, so prefer the
        native short temp filesystem when it exists.
        """
        candidates = []
        # Prefer the native OHOS temp filesystem first: AF_UNIX socket
        # files must be creatable there, and inherited CI TMPDIRs such as
        # /data/storage/el2/base/cache may reject socket binds (EACCES /
        # EADDRINUSE surfaced via swrap_listen on unbound sockets — see
        # PR #7709 CI rounds). Only fall back to the inherited TMPDIR.
        candidates.append("/data/storage/el2/base/temp")
        candidates.append("/tmp")
        inherited = os.environ.get("TMPDIR")
        if inherited:
            candidates.append(inherited)
        # keep the last resort as short as possible
        candidates.append(os.path.join(self.build_folder, "t"))
        for candidate in candidates:
            if candidate and len(candidate) + len("/w_XXXXXX") <= 90:
                # Unique subdirectory per run: torture_setup_socket_dir
                # uses fixed-name AF_UNIX socket files inside TMPDIR, so
                # concurrent CI jobs (or leftover files from a previous
                # round sharing e.g. /data/storage/el2/base/cache) collide
                # with EADDRINUSE. A per-run directory makes that
                # impossible regardless of the host TMPDIR.
                unique = os.path.join(candidate, "swrap-" + uuid.uuid4().hex[:8])
                try:
                    os.makedirs(unique, exist_ok=True)
                    return unique
                except OSError:
                    continue
                if os.path.isdir(candidate) and os.access(candidate, os.W_OK):
                    return os.path.join(candidate, "swrap-%s" % os.getpid())
        return os.path.join(self.build_folder, "upstream-test-runtime")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if str(self.settings.os) == "OHOS":
            self._sign_shared_objects()

    def _sign_shared_objects(self):
        self._sign_elf_files(
            glob.glob(
                os.path.join(self.package_folder, "lib", "**", "*.so*"),
                recursive=True,
            )
        )

    def _sign_upstream_test_artifacts(self):
        candidates = glob.glob(
            os.path.join(self.build_folder, "**", "*.so*"), recursive=True
        )
        for test_name in (
            "echo_srv",
            "calc_unix_scm_rights_payload",
            "test_ioctl",
            "test_tcp_listen",
            "test_tcp_dup2",
            "test_fcntl",
            "test_fcntl_lock",
            "test_echo_tcp_connect",
            "test_echo_tcp_bind",
            "test_echo_tcp_socket_options",
            "test_echo_tcp_sendmsg_recvmsg",
            "test_echo_tcp_sendmmsg_recvmmsg",
            "test_echo_tcp_write_read",
            "test_echo_tcp_poll",
            "test_echo_tcp_writev_readv",
            "test_echo_tcp_get_peer_sock_name",
            "test_echo_udp_sendto_recvfrom",
            "test_echo_udp_send_recv",
            "test_echo_udp_sendmsg_recvmsg",
            "test_max_sockets",
            "test_public_functions",
            "test_close_failure",
            "test_tcp_socket_overwrite",
            "test_syscall_uwrap",
            "test_thread_sockets",
            "test_thread_echo_tcp_connect",
            "test_thread_echo_tcp_write_read",
            "test_thread_echo_tcp_sendmsg_recvmsg",
            "test_thread_echo_udp_send_recv",
            "test_sendmsg_recvmsg_fd",
            "test_echo_tcp_sendmsg_recvmsg_fd",
            "test_fork_thread_deadlock",
            "test_swrap_unit",
        ):
            candidates.extend(
                glob.glob(
                    os.path.join(self.build_folder, "**", test_name),
                    recursive=True,
                )
            )
        self._sign_elf_files(candidates)

    def _sign_elf_files(self, candidates):
        paths = sorted(
            {
                path
                for path in candidates
                if os.path.isfile(path)
                and not os.path.islink(path)
                and self._is_elf(path)
            }
        )
        if not paths:
            return

        objcopy = self._find_ohos_tool("OHOS_LLVM_OBJCOPY", "llvm-objcopy")
        signer = self._find_ohos_tool("OHOS_BINARY_SIGN_TOOL", "binary-sign-tool")
        missing = [
            name
            for name, path in (
                ("llvm-objcopy", objcopy),
                ("binary-sign-tool", signer),
            )
            if not path
        ]
        if missing:
            raise ConanException(
                "OHOS signing tools unavailable: %s" % ", ".join(missing)
            )
        for path in paths:
            strip_result = self.run(
                f'{objcopy} --remove-section .codesign "{path}"',
                ignore_errors=True,
            )
            if strip_result != 0:
                raise ConanException(
                    "llvm-objcopy could not remove .codesign from %s" % path
                )
            sign_result = self.run(
                f'{signer} sign -inFile "{path}" -outFile "{path}" -selfSign 1',
                ignore_errors=True,
            )
            if sign_result != 0:
                raise ConanException("binary-sign-tool failed for %s" % path)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _find_ohos_tool(env_name, command):
        configured = os.environ.get(env_name)
        if configured:
            found = shutil.which(configured)
            if found:
                return found
            if os.path.isfile(configured):
                return configured
        tool_dir = os.environ.get("SIGN_TOOL_PATH")
        if tool_dir:
            candidate = os.path.join(tool_dir, command)
            if os.path.isfile(candidate):
                return candidate
        return shutil.which(command)

    def package_info(self):
        libdir = os.path.join(self.package_folder, "lib")
        wrapper_path = os.path.join(libdir, "libsocket_wrapper.so")

        self.cpp_info.set_property("cmake_file_name", "socket_wrapper")
        self.cpp_info.set_property("cmake_target_name", "socket_wrapper::socket_wrapper")
        self.cpp_info.set_property("pkg_config_name", "socket_wrapper")
        self.cpp_info.libs = ["socket_wrapper_noop"]

        self.runenv_info.define_path("SOCKET_WRAPPER_LIB", wrapper_path)
        self.buildenv_info.define_path("SOCKET_WRAPPER_LIB", wrapper_path)
        self.runenv_info.append_path("LD_LIBRARY_PATH", libdir)
