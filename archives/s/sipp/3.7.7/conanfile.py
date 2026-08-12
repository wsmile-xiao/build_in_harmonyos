#!/usr/bin/env python3
"""Conan recipe for SIPp 3.7.7."""

import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file


class SippConan(ConanFile):
    name = "sipp"
    version = "3.7.7"
    description = "Traffic generator for the SIP protocol"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/SIPp/sipp"
    url = "https://github.com/SIPp/sipp"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("gtest/1.17.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        get(
            self,
            **self.conan_data["ncurses_sources"],
            destination=os.path.join(self.source_folder, "_deps", "ncurses"),
            strip_root=True,
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["USE_SSL"] = "OFF"
        tc.variables["USE_PCAP"] = "OFF"
        tc.variables["USE_SCTP"] = "OFF"
        tc.variables["USE_GSL"] = "OFF"
        tc.variables["BUILD_STATIC"] = False
        tc.variables["USE_ASAN"] = False
        tc.variables["SIPP_USE_CONAN_GTEST"] = "ON"
        if "gtest" in self.dependencies:
            tc.variables["GTEST_GMOCK_LIBRARY"] = os.path.join(
                self.dependencies["gtest"].cpp_info.libdirs[0], "libgmock.a"
            )

        ncurses_prefix = self._ncurses_prefix()
        include_dir = os.path.join(ncurses_prefix, "include")
        tc.variables["CURSES_LIBRARY"] = os.path.join(ncurses_prefix, "lib", "libncursesw.a")
        tc.variables["CURSES_LIBRARY_INCLUDE_DIRS"] = ";".join([include_dir, os.path.join(include_dir, "ncursesw")])
        tc.generate()

    def build(self):
        self._build_private_ncurses()
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        replace_in_file(
            self,
            cmake_lists,
            'if(CMAKE_SYSTEM_NAME STREQUAL "Linux" AND TINFO_LIBRARY)',
            'if((CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS") AND TINFO_LIBRARY)',
            strict=False,
        )
        replace_in_file(
            self,
            cmake_lists,
            """if(EXISTS ${PROJECT_SOURCE_DIR}/gtest/googletest)
  add_sipp_target(sipp_unittest
    EXCLUDE_FROM_ALL
    SOURCES "${PROJECT_SOURCE_DIR}/src/sipp_unittest.cpp"
            "${PROJECT_SOURCE_DIR}/gtest/googletest/src/gtest-all.cc"
            "${PROJECT_SOURCE_DIR}/gtest/googlemock/src/gmock-all.cc"
    COMPILE_DEFINITIONS "-DGTEST"
    EXTRA_INCLUDES ${PROJECT_SOURCE_DIR}/gtest/googletest
                   ${PROJECT_SOURCE_DIR}/gtest/googlemock
                   ${PROJECT_SOURCE_DIR}/gtest/googletest/include
                   ${PROJECT_SOURCE_DIR}/gtest/googlemock/include
  )
else()
  add_sipp_target(sipp_unittest
    EXCLUDE_FROM_ALL
    SOURCES "${PROJECT_SOURCE_DIR}/src/sipp_unittest.cpp"
  )
endif()""",
            """if(SIPP_USE_CONAN_GTEST)
  find_package(gtest REQUIRED)
  add_sipp_target(sipp_unittest
    EXCLUDE_FROM_ALL
    SOURCES "${PROJECT_SOURCE_DIR}/src/sipp_unittest.cpp"
    COMPILE_DEFINITIONS "-DGTEST"
  )
  target_link_libraries(sipp_unittest gtest::gtest)
  if(GTEST_GMOCK_LIBRARY)
    target_link_libraries(sipp_unittest "${GTEST_GMOCK_LIBRARY}")
  endif()
elseif(EXISTS ${PROJECT_SOURCE_DIR}/gtest/googletest)
  add_sipp_target(sipp_unittest
    EXCLUDE_FROM_ALL
    SOURCES "${PROJECT_SOURCE_DIR}/src/sipp_unittest.cpp"
            "${PROJECT_SOURCE_DIR}/gtest/googletest/src/gtest-all.cc"
            "${PROJECT_SOURCE_DIR}/gtest/googlemock/src/gmock-all.cc"
    COMPILE_DEFINITIONS "-DGTEST"
    EXTRA_INCLUDES ${PROJECT_SOURCE_DIR}/gtest/googletest
                   ${PROJECT_SOURCE_DIR}/gtest/googlemock
                   ${PROJECT_SOURCE_DIR}/gtest/googletest/include
                   ${PROJECT_SOURCE_DIR}/gtest/googlemock/include
  )
else()
  add_sipp_target(sipp_unittest
    EXCLUDE_FROM_ALL
    SOURCES "${PROJECT_SOURCE_DIR}/src/sipp_unittest.cpp"
  )
endif()

if(TARGET sipp_unittest)
  enable_testing()
  add_test(NAME sipp_unittest COMMAND sipp_unittest)
endif()""",
            strict=False,
        )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if "gtest" in self.dependencies:
            cmake.build(target="sipp_unittest")
            self.run("ctest --output-on-failure", cwd=self.build_folder, env=["conanbuild"], ignore_errors=False)
        else:
            self.run("ctest -N", cwd=self.build_folder, env=["conanbuild"], ignore_errors=False)

    def _ncurses_prefix(self):
        return os.path.join(self.build_folder, "_private_ncurses")

    def _build_private_ncurses(self):
        source_dir = os.path.join(self.source_folder, "_deps", "ncurses")
        prefix = self._ncurses_prefix()
        stamp = os.path.join(prefix, ".built")
        if os.path.exists(stamp):
            return

        config_shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
        if not config_shell:
            raise RuntimeError("bash is required to build private ncurses")
        tool_bin = os.path.dirname(config_shell)
        cc = os.environ.get("CC") or self._tool_from_bin(tool_bin, "clang")
        cxx = os.environ.get("CXX") or self._tool_from_bin(tool_bin, "clang++")
        ar = os.environ.get("AR") or self._tool_from_bin(tool_bin, "llvm-ar")
        ranlib = os.environ.get("RANLIB") or self._tool_from_bin(tool_bin, "llvm-ranlib")
        strip = os.environ.get("STRIP") or self._tool_from_bin(tool_bin, "llvm-strip")
        tmpdir = os.path.join(self.build_folder, "_private_ncurses_tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o700)
        os.makedirs(prefix, exist_ok=True)

        saved_env = {name: os.environ.get(name) for name in ("CONFIG_SHELL", "SHELL", "TMPDIR", "PATH", "CC", "CXX", "AR", "RANLIB", "STRIP")}
        try:
            os.environ["CONFIG_SHELL"] = config_shell
            os.environ["SHELL"] = config_shell
            os.environ["TMPDIR"] = tmpdir
            os.environ["PATH"] = os.pathsep.join([tool_bin, os.environ.get("PATH", "")])
            os.environ["CC"] = cc
            os.environ["CXX"] = cxx
            os.environ["AR"] = ar
            os.environ["RANLIB"] = ranlib
            os.environ["STRIP"] = strip

            self._patch_ncurses_configure(source_dir, config_shell, tmpdir)
            configure_args = [
                shlex.quote(config_shell),
                shlex.quote(os.path.join(source_dir, "configure")),
                shlex.quote(f"--prefix={prefix}"),
                "--without-shared",
                "--without-debug",
                "--without-ada",
                "--without-manpages",
                "--without-tests",
                "--without-cxx-binding",
                "--enable-widec",
                "--enable-overwrite",
                "--no-create",
            ]
            self.run(" ".join(configure_args), cwd=source_dir, env=["conanbuild"], ignore_errors=False)
            self._patch_ncurses_config_status(source_dir, tmpdir)
            self.run(
                shlex.quote(config_shell) + " ./config.status",
                cwd=source_dir,
                env=["conanbuild"],
                ignore_errors=False,
            )
            self._patch_ncurses_makefiles(source_dir)
            self.run("make -j1 preinstall", cwd=source_dir, env=["conanbuild"], ignore_errors=False)
            self.run("make -j1", cwd=source_dir, env=["conanbuild"], ignore_errors=False)
            self.run("make install", cwd=source_dir, env=["conanbuild"], ignore_errors=False)
            with open(stamp, "w", encoding="utf-8") as file:
                file.write("ok\n")
        finally:
            for name, value in saved_env.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    def _tool_from_bin(self, tool_bin, name):
        path = os.path.join(tool_bin, name)
        return path if os.path.exists(path) else name

    def _patch_ncurses_configure(self, source_dir, config_shell, tmpdir):
        replace_in_file(
            self,
            os.path.join(source_dir, "config.guess"),
            """    *:Minix:*:*)
	GUESS=$UNAME_MACHINE-unknown-minix
	;;""",
            """    *:Minix:*:*)
	GUESS=$UNAME_MACHINE-unknown-minix
	;;
    *:HarmonyOS:*:*)
	case "$UNAME_MACHINE" in
	    aarch64|arm64)
		MACHINE=aarch64
		;;
	    armv7*|armv8*)
		MACHINE=arm
		;;
	    x86_64|amd64)
		MACHINE=x86_64
		;;
	    i?86)
		MACHINE=i686
		;;
	    *)
		MACHINE="$UNAME_MACHINE"
		;;
	esac
	GUESS=${MACHINE}-unknown-linux-ohos
	;;""",
            strict=False,
        )
        replace_in_file(
            self,
            os.path.join(source_dir, "config.sub"),
            "| fiwix* | mlibc* | cos* | mbr* | ironclad* )",
            "| fiwix* | mlibc* | cos* | mbr* | ironclad* | ohos* )",
            strict=False,
        )
        replace_in_file(
            self,
            os.path.join(source_dir, "config.sub"),
            "| linux-relibc*- | linux-uclibc*- )",
            "| linux-relibc*- | linux-uclibc*- | linux-ohos*- )",
            strict=False,
        )
        replace_in_file(
            self,
            os.path.join(source_dir, "configure"),
            "#! /bin/sh",
            f"#! /bin/sh\nCONFIG_SHELL={shlex.quote(config_shell)}\nSHELL={shlex.quote(config_shell)}\nTMPDIR={shlex.quote(tmpdir)}\nexport CONFIG_SHELL SHELL TMPDIR",
            strict=False,
        )
        replace_in_file(self, os.path.join(source_dir, "configure"), "umask 077", "umask 022", strict=False)
        replace_in_file(
            self,
            os.path.join(source_dir, "configure"),
            'fi\n${MAKE:-make} preinstall',
            'fi\nif test "$no_create" != yes; then\n  ${MAKE:-make} preinstall\nfi',
            strict=False,
        )

    def _patch_ncurses_config_status(self, source_dir, tmpdir):
        config_status = os.path.join(source_dir, "config.status")
        fixed_tmp = os.path.join(tmpdir, "ncurses-config-status")
        os.makedirs(fixed_tmp, exist_ok=True)
        os.chmod(fixed_tmp, 0o700)
        with open(config_status, "r", encoding="utf-8") as file:
            content = file.read()

        content = content.replace("umask 077", "umask 022")
        content = content.replace('ac_dir=`$as_expr X"$ac_file" :', 'ac_dir=`false && $as_expr X"$ac_file" :', 1)
        for umask in ("077", "000", "022"):
            content = content.replace(
                f'tmp=`(umask {umask} && mktemp -d -q "$TMPDIR/csXXXXXX") 2>/dev/null` &&\n'
                '  test -n "$tmp" && test -d "$tmp"',
                f'tmp={shlex.quote(fixed_tmp)} &&\n'
                '  rm -rf "$tmp" && mkdir -p "$tmp" && chmod u+rwx "$tmp" && test -d "$tmp"',
            )
            content = content.replace(
                f'tmp=$TMPDIR/cs$$-$RANDOM\n  (umask {umask} && mkdir "$tmp")',
                f'tmp={shlex.quote(fixed_tmp)}\n  rm -rf "$tmp" && mkdir -p "$tmp" && chmod u+rwx "$tmp"',
            )

        with open(config_status, "w", encoding="utf-8") as file:
            file.write(content)

    def _patch_ncurses_makefiles(self, source_dir):
        makefiles = {
            "Makefile": ".",
            "include/Makefile": "..",
            "ncurses/Makefile": "..",
            "progs/Makefile": "..",
            "panel/Makefile": "..",
            "menu/Makefile": "..",
            "form/Makefile": "..",
            "misc/Makefile": "..",
        }
        pattern = re.compile(r"^(\s*)(VPATH|top_srcdir|srcdir)(\s*=).*$")
        for rel_path, top_srcdir in makefiles.items():
            path = os.path.join(source_dir, *rel_path.split("/"))
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8", errors="surrogateescape") as file:
                lines = file.readlines()
            patched = []
            changed = False
            for line in lines:
                match = pattern.match(line.rstrip("\n"))
                if match:
                    value = top_srcdir if match.group(2) == "top_srcdir" else "."
                    line = f"{match.group(1)}{match.group(2)}={value}\n"
                    changed = True
                patched.append(line)
            if changed:
                with open(path, "w", encoding="utf-8", errors="surrogateescape") as file:
                    file.writelines(patched)

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "sipp", self.build_folder, os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(
            self,
            "*.xml",
            os.path.join(self.source_folder, "sipp_scenarios"),
            os.path.join(self.package_folder, "res", "sipp_scenarios"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
