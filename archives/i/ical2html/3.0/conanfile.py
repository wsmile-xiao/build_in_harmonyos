#!/usr/bin/env python3

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import (
    get,
    copy,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain


def _sign_elf(conan, bin_path):
    sign_tool = "/data/service/hnp/bin/binary-sign-tool"
    objcopy = "/data/service/hnp/bin/llvm-objcopy"

    if not os.path.exists(sign_tool):
        conan.output.info("binary-sign-tool not found, skipping ELF signing")
        return

    subprocess.run(
        [objcopy, "--remove-section", ".codesign", bin_path],
        capture_output=True,
        timeout=10
    )

    tmp = bin_path + ".signed.tmp"

    for _ in range(3):
        result = subprocess.run(
            [
                sign_tool,
                "sign",
                "-inFile", bin_path,
                "-outFile", tmp,
                "-selfSign", "1",
            ],
            capture_output=True,
            timeout=30
        )

        if result.returncode == 0 and os.path.exists(tmp):
            shutil.move(tmp, bin_path)
            os.chmod(bin_path, 0o755)
            return

    if os.path.exists(tmp):
        os.remove(tmp)

    raise ConanException(f"ELF signing failed for {bin_path}")
class Ical2htmlConan(ConanFile):
    name = "ical2html"
    version = "3.0"
    package_type = "application"

    description = "Convert iCalendar files to HTML and manipulate iCalendar data"
    license = "W3C"
    homepage = "https://www.w3.org/Tools/Ical2html/"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "."

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ical2html requires Linux or OHOS, got {self.settings.os}"
            )

    def source(self):
        sources = self.conan_data["sources"]

        get(
            self,
            url=sources[0]["url"],
            sha256=sources[0]["sha256"],
            strip_root=True
        )

        get(
            self,
            url=sources[1]["url"],
            sha256=sources[1]["sha256"],
            destination="_libical",
            strip_root=True
        )

    def generate(self):
        stage = os.path.join(self.build_folder, "_stage")

        cc, cxx = self._compiler_paths()

        shell = shutil.which("bash") or shutil.which("sh") or "/bin/sh"
        if not os.path.exists(shell):
            raise ConanException(f"Shell not found: {shell}")

        self.output.info(f"Using configure shell: {shell}")

        tc = AutotoolsToolchain(self)

        tc.extra_cflags = [
            f"-I{os.path.join(stage, 'include')}",
            f"-I{os.path.join(stage, 'include', 'libical')}",
        ]

        tc.extra_ldflags = [
            f"-L{os.path.join(stage, 'lib')}",
        ]

        env = tc.environment()

        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)

        env.prepend_path(
            "PKG_CONFIG_PATH",
            os.path.join(stage, "lib", "pkgconfig")
        )

        env.define("LIBS", "-lical -lpthread -lm")

        tc.generate(env)

    def _compiler_paths(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict
        )

        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")

        if not os.path.exists(cc):
            cc = shutil.which("clang") or cc

        if not os.path.exists(cxx):
            cxx = shutil.which("clang++") or cxx

        if not os.path.exists(cc):
            raise ConanException(f"C compiler not found: {cc}")

        if not os.path.exists(cxx):
            raise ConanException(f"C++ compiler not found: {cxx}")

        self.output.info(f"Using C compiler: {cc}")
        self.output.info(f"Using C++ compiler: {cxx}")

        return cc, cxx
    def _build_libical(self):
        cc, cxx = self._compiler_paths()

        cmake = shutil.which("cmake")

        if not cmake:
            candidates = [
                os.path.expanduser("~/usr/local/bin/cmake"),
                "/data/service/hnp/bin/cmake",
                "/data/app/bin/cmake",
            ]

            for candidate in candidates:
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    cmake = candidate
                    break

        if not cmake:
            raise ConanException("cmake not found")

        self.output.info(f"Using CMake: {cmake}")

        libical_source = os.path.join(self.source_folder, "_libical")
        libical_build = os.path.join(self.build_folder, "_libical_build")
        stage = os.path.join(self.build_folder, "_stage")

        shutil.rmtree(libical_build, ignore_errors=True)
        shutil.rmtree(stage, ignore_errors=True)

        os.makedirs(libical_build, exist_ok=True)
        os.makedirs(stage, exist_ok=True)

        arch_map = {
            "armv8": "aarch64",
            "x86_64": "x86_64",
        }
        processor = arch_map.get(str(self.settings.arch), str(self.settings.arch))

        command = [
            cmake,
            "-S", libical_source,
            "-B", libical_build,
            "-DCMAKE_SYSTEM_NAME=Linux",
            f"-DCMAKE_SYSTEM_PROCESSOR={processor}",
            f"-DCMAKE_C_COMPILER={cc}",
            f"-DCMAKE_CXX_COMPILER={cxx}",
            f"-DCMAKE_INSTALL_PREFIX={stage}",
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DSTATIC_ONLY=ON",
            "-DSHARED_ONLY=OFF",
            "-DICAL_GLIB=OFF",
            "-DICAL_BUILD_DOCS=OFF",
            "-DICAL_BUILD_EXAMPLES=OFF",
            "-DICAL_BUILD_TESTING=OFF",
        ]

        subprocess.run(command, check=True)

        subprocess.run(
            [
                cmake,
                "--build", libical_build,
                "--target", "install",
                "--parallel", "1",
            ],
            check=True
        )
    def build(self):
        apply_conandata_patches(self)
        self._build_libical()

        stage = os.path.join(self.build_folder, "_stage")

        cc, cxx = self._compiler_paths()

        shell = shutil.which("bash") or shutil.which("sh")
        if not shell:
            raise ConanException("No usable shell found")

        make = shutil.which("make")
        if not make:
            raise ConanException("make not found")

        pkg_config = os.path.join(stage, "lib", "pkgconfig")

        env = os.environ.copy()
        env["PWD"] = self.build_folder

        old_pkg_config = env.get("PKG_CONFIG_PATH", "")

        env.update({
            "CC": cc,
            "CXX": cxx,
            "CONFIG_SHELL": shell,
            "SHELL": shell,
            "CPPFLAGS": (
                f"-I{os.path.join(stage, 'include')} "
                f"-I{os.path.join(stage, 'include', 'libical')}"
            ),
            "LDFLAGS": f"-L{os.path.join(stage, 'lib')}",
            "LIBS": "-lical -lpthread -lm",
            "PKG_CONFIG_PATH": (
                pkg_config
                if not old_pkg_config
                else f"{pkg_config}:{old_pkg_config}"
            ),
        })

        autoconf_tools = os.path.join(
            self.build_folder,
            "_autoconf_tools"
        )
        os.makedirs(autoconf_tools, exist_ok=True)

        mktemp_wrapper = os.path.join(
            autoconf_tools,
            "mktemp"
        )

        with open(mktemp_wrapper, "w") as f:
            f.write(f"#!{shell}\\nexit 1\\n")

        os.chmod(mktemp_wrapper, 0o755)

        env["PATH"] = (
            f"{autoconf_tools}:"
            f"{env.get('PATH', '')}"
        )

        self.output.info(
            "Using mkdir fallback for Autoconf temporary directories"
        )
        self.output.info(f"ical2html CC: {cc}")
        self.output.info(f"ical2html CXX: {cxx}")
        self.output.info(f"ical2html shell: {shell}")
        self.output.info(f"ical2html make: {make}")
        self.output.info(f"ical2html PWD: {env['PWD']}")

        configure = os.path.join(self.build_folder, "configure")

        subprocess.run(
            [
                shell,
                configure,
                "--prefix=/",
            ],
            check=True,
            cwd=self.build_folder,
            env=env,
        )

        subprocess.run(
            [
                make,
                "-j1",
            ],
            check=True,
            cwd=self.build_folder,
            env=env,
        )
    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")

        for program in ("ical2html", "icalfilter", "icalmerge"):
            copy(
                self,
                program,
                src=self.build_folder,
                dst=bin_dir
            )

            path = os.path.join(bin_dir, program)
            if os.path.exists(path):
                _sign_elf(self, path)

        copy(
            self,
            "calendar.css",
            src=self.source_folder,
            dst=os.path.join(
                self.package_folder,
                "share",
                "ical2html"
            )
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share/ical2html"]
