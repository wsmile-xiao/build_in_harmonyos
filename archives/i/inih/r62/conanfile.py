"""Pure C inih r62 static package with the 15 upstream test configurations."""

import hashlib
import os
import shlex
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


UPSTREAM_TESTS = (
    ("multi", "unittest.c", ()),
    ("multi_max_line", "unittest.c", ("-DINI_MAX_LINE=20",)),
    ("single", "unittest.c", ("-DINI_ALLOW_MULTILINE=0",)),
    ("disallow_inline_comments", "unittest.c", ("-DINI_ALLOW_INLINE_COMMENTS=0",)),
    ("stop_on_first_error", "unittest.c", ("-DINI_STOP_ON_FIRST_ERROR=1",)),
    ("handler_lineno", "unittest.c", ("-DINI_HANDLER_LINENO=1",)),
    ("string", "unittest_string.c", ("-DINI_MAX_LINE=20",)),
    ("heap", "unittest.c", ("-DINI_USE_STACK=0",)),
    ("heap_max_line", "unittest.c", (
        "-DINI_USE_STACK=0", "-DINI_MAX_LINE=20", "-DINI_INITIAL_ALLOC=20")),
    ("heap_realloc", "unittest.c", (
        "-DINI_USE_STACK=0", "-DINI_ALLOW_REALLOC=1", "-DINI_INITIAL_ALLOC=5")),
    ("heap_realloc_max_line", "unittest.c", (
        "-DINI_USE_STACK=0", "-DINI_MAX_LINE=20", "-DINI_ALLOW_REALLOC=1",
        "-DINI_INITIAL_ALLOC=5")),
    ("heap_string", "unittest_string.c", (
        "-DINI_USE_STACK=0", "-DINI_MAX_LINE=20", "-DINI_INITIAL_ALLOC=20")),
    ("call_handler_on_new_section", "unittest.c", (
        "-DINI_CALL_HANDLER_ON_NEW_SECTION=1",)),
    ("allow_no_value", "unittest.c", ("-DINI_ALLOW_NO_VALUE=1",)),
    ("alloc", "unittest_alloc.c", (
        "-DINI_CUSTOM_ALLOCATOR=1", "-DINI_USE_STACK=0",
        "-DINI_ALLOW_REALLOC=1", "-DINI_INITIAL_ALLOC=12")),
)


def _shell_command(args):
    args = [str(arg) for arg in args]
    if os.name == "nt":
        return subprocess.list2cmdline(args)
    return " ".join(shlex.quote(arg) for arg in args)


class InihConan(ConanFile):
    name = "inih"
    version = "r62"
    description = "Small INI file parser in C"
    homepage = "https://github.com/benhoyt/inih"
    license = "BSD-3-Clause"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c")
        if not cc:
            raise ConanInvalidConfiguration(
                "A target C compiler is required in tools.build:compiler_executables"
            )
        cc_path = Path(cc)
        ar_path = Path(compiler_executables.get("ar") or
                       cc_path.with_name("llvm-ar" + cc_path.suffix))
        if not cc_path.is_file() or not ar_path.is_file():
            raise ConanInvalidConfiguration(
                f"Target compiler or archive tool missing: {cc_path}, {ar_path}"
            )

        source = Path(self.source_folder)
        build = Path(self.build_folder)
        build.mkdir(parents=True, exist_ok=True)
        compile_flags = ["-std=c99", "-Wall", "-Wextra", "-fPIC"]
        if str(self.settings.build_type) == "Debug":
            compile_flags.extend(["-g", "-O0"])
        else:
            compile_flags.append("-O2")
        compile_flags.append("-I" + str(source))

        obj = build / "ini.o"
        library = build / "libinih.a"
        self.run(_shell_command([cc, *compile_flags, "-c", source / "ini.c", "-o", obj]))
        self.run(_shell_command([ar_path, "rcs", library, obj]))

        test_dir = source / "tests"
        executable_suffix = ".exe" if os.name == "nt" and can_run(self) else ""
        for name, test_source, macros in UPSTREAM_TESTS:
            test_bin = build / ("unittest_" + name + executable_suffix)
            self.run(_shell_command([
                cc, *compile_flags, *macros, source / "ini.c",
                test_dir / test_source, "-o", test_bin,
            ]))
            if not can_run(self):
                continue
            result = subprocess.run(
                [str(test_bin)], cwd=test_dir, capture_output=True, timeout=60
            )
            actual_path = build / ("upstream-" + name + ".actual")
            actual_path.write_bytes(result.stdout)
            expected = (test_dir / ("baseline_" + name + ".txt")).read_bytes()
            if result.returncode != 0 or result.stdout != expected:
                error_text = result.stderr[:2048].decode("utf-8", errors="replace")
                raise ConanException(
                    f"Upstream test {name} failed: return={result.returncode}, "
                    f"expected_bytes={len(expected)}, actual_bytes={len(result.stdout)}, "
                    f"stderr={error_text}"
                )
            digest = hashlib.sha256(result.stdout).hexdigest()
            self.output.info(f"UPSTREAM_TEST_PASS {name} bytes={len(expected)} sha256={digest}")
        if can_run(self):
            self.output.info("UPSTREAM_TESTS_PASS 15/15")
        else:
            self.output.info("Cross build: 15 upstream test binaries compiled; target execution required")

    def package(self):
        copy(self, "ini.h", self.source_folder,
             os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "libinih.a", self.build_folder,
             os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["inih"]
        self.cpp_info.set_property("cmake_file_name", "inih")
        self.cpp_info.set_property("cmake_target_name", "inih::inih")
