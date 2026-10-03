"""Shmdata 1.3.74 for HarmonyOS PC."""

import os
import re
import socket
import tempfile
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class ShmdataConan(ConanFile):
    name = "shmdata"
    version = "1.3.74"
    description = "Shared-memory data-flow transport over Unix sockets and SysV IPC"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.com/nicobou/shmdata"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    exports_sources = "patches/*"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def configure(self):
        if not self.options.shared:
            raise ConanInvalidConfiguration("this recipe requires the upstream shared target")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("SHMDATA_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("SHMDATA_SOURCE_ARCHIVE must be a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["WITH_GST"] = False
        toolchain.variables["WITH_PYTHON"] = False
        toolchain.variables["WITH_SDFLOW"] = True
        toolchain.variables["WITH_SDCRASH"] = True
        toolchain.variables["TEST_COVERAGE"] = False
        toolchain.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        toolchain.generate()

    def _prepare_ohos_tests(self):
        """Keep filesystem-socket semantics on a directory that permits bind."""
        socket_dir = None
        for base in ("/data/storage/el2/base/files", "/data/local/tmp"):
            if not os.path.isdir(base):
                continue
            try:
                candidate = tempfile.mkdtemp(prefix="shmdata-sock-", dir=base)
                probe = os.path.join(candidate, "probe")
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                    sock.bind(probe)
                os.unlink(probe)
                socket_dir = candidate
                break
            except OSError as exc:
                self.output.warning(f"AF_UNIX bind unavailable in {base}: {exc}")
        if socket_dir is None:
            raise ConanInvalidConfiguration("no writable OHOS filesystem-socket directory")
        self.output.info(f"OHOS_TEST_SOCKET_DIR={socket_dir}")
        tests = Path(self.source_folder, "tests")
        changed = 0
        for path in sorted(tests.glob("check-*")):
            if path.suffix not in (".cpp", ".sh"):
                continue
            data = path.read_text(encoding="utf-8")
            revised = data.replace('"/tmp/check-', f'"{socket_dir}/check-')
            revised = revised.replace(' /tmp/test', f' {socket_dir}/test')
            if revised != data:
                path.write_text(revised, encoding="utf-8")
                changed += 1
        if changed != 13:
            raise ConanInvalidConfiguration(
                f"unexpected number of OHOS test socket path rewrites: {changed}"
            )
        latency = tests / "check-latency.cpp"
        latency_text = latency.read_text(encoding="utf-8")
        old_cast = "std::chrono::duration_cast<std::chrono::microseconds, int64_t>"
        if latency_text.count(old_cast) != 2:
            raise ConanInvalidConfiguration("unexpected latency-test duration_cast calls")
        latency.write_text(
            latency_text.replace(old_cast, "std::chrono::duration_cast<std::chrono::microseconds>"),
            encoding="utf-8",
        )
        cmake_file = tests / "CMakeLists.txt"
        contents = cmake_file.read_text(encoding="utf-8")
        if contents.count("COMMAND bash ${CMAKE_CURRENT_SOURCE_DIR}/check-") != 2:
            raise ConanInvalidConfiguration("unexpected shell test registration")
        contents = contents.replace(
            "COMMAND bash ${CMAKE_CURRENT_SOURCE_DIR}/check-",
            "COMMAND /system/bin/sh ${CMAKE_CURRENT_SOURCE_DIR}/check-",
        )
        old_path = "PATH=${CMAKE_BINARY_DIR}/utils:${PATH}"
        if contents.count(old_path) != 2:
            raise ConanInvalidConfiguration("unexpected shell test PATH")
        contents = contents.replace(old_path, "PATH=${CMAKE_BINARY_DIR}/utils:$ENV{PATH}")
        cmake_file.write_text(contents, encoding="utf-8")

    def _prepare_ohos_ipc(self):
        """Replace the seccomp-blocked SysV backend with POSIX shared memory."""
        target = Path(self.source_folder, "shmdata")
        replacements = {
            "sysv-shm.hpp": ("shmget", "sysVShm"),
            "sysv-shm.cpp": ("shmget", "sysVShm"),
            "sysv-sem.hpp": ("semget", "sysVSem"),
            "sysv-sem.cpp": ("semget", "sysVSem"),
        }
        for name, (_, api) in replacements.items():
            original = (target / name).read_text(encoding="utf-8")
            if api not in original:
                raise ConanInvalidConfiguration("unexpected upstream IPC API: " + name)
            replacement = Path(self.export_sources_folder, "patches", "ohos-posix-" +
                               ("shm" if "shm" in name else "sem") + Path(name).suffix)
            if not replacement.is_file():
                raise ConanInvalidConfiguration("missing POSIX IPC patch: " + name)
            (target / name).write_bytes(replacement.read_bytes())
        # CMake does not set UNIX for its OHOS system name, although this
        # target has the Unix pkg-config layout used by upstream.
        cmake_file = target / "CMakeLists.txt"
        cmake_text = cmake_file.read_text(encoding="utf-8")
        if cmake_text.count("if (UNIX)") != 1:
            raise ConanInvalidConfiguration("unexpected pkg-config platform gate")
        cmake_file.write_text(
            cmake_text.replace("if (UNIX)",
                               'if (UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")', 1),
            encoding="utf-8",
        )
        reader_file = target / "reader.cpp"
        reader_text = reader_file.read_text(encoding="utf-8")
        old_resize = """shm_.reset(new sysVShm(ftok(path_.c_str(), 'n'),
                                        0,
                                        log_,"""
        new_resize = old_resize.replace("                                        0,",
                                        "                                        size,")
        if reader_text.count(old_resize) != 1:
            raise ConanInvalidConfiguration("unexpected reader resize attach")
        reader_file.write_text(reader_text.replace(old_resize, new_resize, 1),
                               encoding="utf-8")

    def build(self):
        if str(self.settings.os) == "OHOS":
            header = Path(self.source_folder, "shmdata", "cwriter.h")
            contents = header.read_text(encoding="utf-8")
            anchor = "#include <stdlib.h>"
            if contents.count(anchor) != 1:
                raise ConanInvalidConfiguration("unexpected cwriter.h includes")
            header.write_text(contents.replace(anchor, anchor + "\n#include <sys/types.h>", 1),
                              encoding="utf-8")
            self._prepare_ohos_ipc()
            self._prepare_ohos_tests()
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j2"])
        # The two GStreamer and one Python tests require optional interfaces
        # that are deliberately disabled. Every registered core test runs.
        tests = Path(self.build_folder, "tests", "CTestTestfile.cmake")
        if not tests.is_file():
            raise ConanInvalidConfiguration("CTest registration file missing")
        registered = re.findall(r"(?m)^add_test\(", tests.read_text(encoding="utf-8"))
        if len(registered) != 16:
            raise ConanInvalidConfiguration(
                f"expected 16 registered core tests, found {len(registered)}"
            )
        cmake.ctest(cli_args=["--output-on-failure", "-j1"])
        self.output.info("UPSTREAM_TESTS 16/16 PASS")

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        library = Path(self.package_folder, "lib", "libshmdata-1.3.so")
        if not library.exists():
            raise ConanInvalidConfiguration("shared shmdata library missing")
        pc = Path(self.package_folder, "lib", "pkgconfig", "shmdata-1.3.pc")
        if not pc.is_file():
            raise ConanInvalidConfiguration("shmdata pkg-config file missing")
        data = pc.read_text(encoding="utf-8")
        lines = data.splitlines()
        matches = [i for i, line in enumerate(lines) if line.startswith("prefix=")]
        if len(matches) != 1:
            raise ConanInvalidConfiguration("unexpected shmdata.pc prefix")
        lines[matches[0]] = "prefix=${pcfiledir}/../.."
        pc.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def package_info(self):
        self.cpp_info.libs = ["shmdata-1.3"]
        self.cpp_info.includedirs = ["include/shmdata-1.3"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.set_property("cmake_file_name", "shmdata")
        self.cpp_info.set_property("cmake_target_name", "shmdata::shmdata")
        self.cpp_info.set_property("pkg_config_name", "shmdata-1.3")
