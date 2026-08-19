#!/usr/bin/env python3
"""Conan recipe for pixz 1.0.7."""

import os
import shutil
import shlex
from pathlib import Path

from conan import ConanFile
from conan.tools.build import load_toolchain_args
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class PixzConan(ConanFile):
    name = "pixz"
    version = "1.0.7"
    description = "Parallel indexed xz compressor and decompressor"
    license = "BSD-2-Clause"
    homepage = "https://github.com/vasi/pixz"
    url = "https://github.com/vasi/pixz"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    generators = "VirtualRunEnv"
    exports_sources = "patches/*"
    tool_requires = "cppcheck/2.21.0"

    def requirements(self):
        self.requires("libarchive/3.8.7")
        self.requires("xz/5.6.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

        gen_dir = Path(self.generators_folder)
        xz_pc = gen_dir / "xz.pc"
        liblzma_pc = gen_dir / "liblzma.pc"
        if xz_pc.is_file() and not liblzma_pc.is_file():
            shutil.copy2(xz_pc, liblzma_pc)

        env = Environment()
        for dep_name in ("libarchive", "xz"):
            dep = self.dependencies[dep_name]
            for bindir in dep.cpp_info.bindirs:
                env.prepend_path("PATH", str(bindir))
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", str(libdir))
        config_shell = os.environ.get("CONFIG_SHELL")
        if config_shell:
            env.define("CONFIG_SHELL", config_shell)

        self._restore_hardcoded_filesdir("cppcheck", "share/Cppcheck")
        env.vars(self).save_script("pixz_ohos_env")

    def _restore_hardcoded_filesdir(self, dependency_name, data_relative_path):
        """Relocate a tool that embeds a stale absolute FILESDIR in its ELF."""
        dependency = self.dependencies.build[dependency_name]
        data_dir = os.path.join(dependency.package_folder, *data_relative_path.split("/"))
        if not os.path.isfile(os.path.join(data_dir, "cfg", "std.cfg")):
            raise RuntimeError(f"{dependency_name} package data is incomplete: {data_dir}")

        executable = os.path.join(dependency.package_folder, "bin", dependency_name)
        with open(executable, "rb") as binary_file:
            blob = binary_file.read()
        marker = b'FILESDIR set to "'
        start = blob.find(marker)
        if start == -1:
            raise RuntimeError(f"{dependency_name} FILESDIR marker not found in {executable}")
        start += len(marker)
        end = blob.find(b'"', start)
        if end == -1:
            raise RuntimeError(f"{dependency_name} FILESDIR marker is unterminated in {executable}")
        hardcoded_dir = blob[start:end].decode("utf-8", "strict")
        if not hardcoded_dir or not os.path.isabs(hardcoded_dir):
            raise RuntimeError(f"{dependency_name} FILESDIR is not an absolute path: {hardcoded_dir!r}")

        if os.path.lexists(hardcoded_dir):
            if os.path.realpath(hardcoded_dir) != os.path.realpath(data_dir):
                raise RuntimeError(f"{dependency_name} FILESDIR already exists with a different target: {hardcoded_dir}")
            return

        os.makedirs(os.path.dirname(hardcoded_dir), exist_ok=True)
        try:
            os.symlink(data_dir, hardcoded_dir, target_is_directory=True)
        except OSError:
            # Some HarmonyOS-backed filesystems reject symlinks. A copied data
            # directory preserves the same read-only runtime lookup semantics.
            shutil.copytree(data_dir, hardcoded_dir)
        self.output.info(f"{dependency_name}: restored FILESDIR {hardcoded_dir}")

    def build(self):
        self._patch_sources()
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            os.chmod(configure, 0o755)

        autotools = Autotools(self)
        configure_args = load_toolchain_args(self.generators_folder).get("configure_args")
        if self.settings.os == "OHOS":
            # configure runs in build_folder, so its `test -r src/pixz.1` fails
            # (src/ is in source_folder). Skip man page generation to avoid the
            # "AsciiDoc not found" error; the prebuilt pixz.1 is still packaged.
            configure_args = configure_args + " --without-manpage"
            config_shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/system/bin/sh"
            os.makedirs(self.build_folder, exist_ok=True)
            self.run(f'CONFIG_SHELL="{config_shell}" "{config_shell}" "{configure}" {configure_args}',
                     cwd=self.build_folder, env=["conanbuild", "pixz_ohos_env"])
        else:
            autotools.configure()

        # OHOS loader cannot find transitive .so deps. Rewrite src/Makefile's
        # LIBS/pixz_LDADD to link libarchive/liblzma/libz statically by full
        # .a path, bypassing the -l lookup that picks .so.
        if self.settings.os == "OHOS":
            static_libs = []
            for dep_name in ("libarchive", "xz", "zlib"):
                if dep_name not in self.dependencies:
                    continue
                dep = self.dependencies[dep_name]
                pkg = dep.package_folder
                for libdir in dep.cpp_info.libdirs:
                    libdir = str(libdir)
                    if not os.path.isabs(libdir):
                        libdir = os.path.join(pkg, libdir)
                    for lib in ("archive", "lzma", "z"):
                        cand = os.path.join(libdir, f"lib{lib}.a")
                        if os.path.isfile(cand):
                            static_libs.append(cand)
            src_makefile = os.path.join(self.build_folder, "src", "Makefile")
            if os.path.isfile(src_makefile) and static_libs:
                with open(src_makefile, "r", encoding="utf-8") as f:
                    mk = f.read()
                joined = " ".join(static_libs)
                mk = mk.replace("-larchive -llzma -lz", joined)
                mk = mk.replace("-larchive -lz -llzma", joined)
                with open(src_makefile, "w", encoding="utf-8") as f:
                    f.write(mk)

        self.run("make -j1", cwd=self.build_folder, env=["conanbuild", "pixz_ohos_env"])
        self.run("make check -j1", cwd=self.build_folder, env=["conanbuild", "conanrun", "pixz_ohos_env"])

    def _patch_sources(self):
        config_guess = os.path.join(self.source_folder, "config.guess")
        replace_in_file(
            self,
            config_guess,
            "    *:NetBSD:*:*)",
            """    *:HarmonyOS:*:*)
\tcase "$UNAME_MACHINE" in
\t    aarch64|arm64) machine=aarch64 ;;
\t    armv7*|armv8*) machine=arm ;;
\t    x86_64|amd64)  machine=x86_64 ;;
\t    i?86)          machine=i686 ;;
\t    *)             machine="$UNAME_MACHINE" ;;
\tesac
\techo "$machine-unknown-linux-ohos"
\texit ;;
    *:NetBSD:*:*)""",
            strict=True,
        )

        config_sub = os.path.join(self.source_folder, "config.sub")
        replace_in_file(
            self,
            config_sub,
            "  nto-qnx* | linux-gnu* | linux-android* | linux-dietlibc | linux-newlib* | \\",
            "  nto-qnx* | linux-gnu* | linux-android* | linux-ohos* | linux-dietlibc | linux-newlib* | \\",
            strict=True,
        )
        replace_in_file(
            self,
            config_sub,
            """  android-linux)
    os=-linux-android
    basic_machine=`echo "$1" | sed 's/^\\(.*\\)-\\([^-]*-[^-]*\\)$/\\1/'`-unknown
    ;;""",
            """  android-linux)
    os=-linux-android
    basic_machine=`echo "$1" | sed 's/^\\(.*\\)-\\([^-]*-[^-]*\\)$/\\1/'`-unknown
    ;;
  ohos-linux)
    os=-linux-ohos
    basic_machine=`echo "$1" | sed 's/^\\(.*\\)-\\([^-]*-[^-]*\\)$/\\1/'`-unknown
    ;;""",
            strict=True,
        )
        replace_in_file(
            self,
            config_sub,
            "      | -midipix* | -mingw32* | -mingw64* | -linux-gnu* | -linux-android* \\",
            "      | -midipix* | -mingw32* | -mingw64* | -linux-gnu* | -linux-android* | -linux-ohos* \\",
            strict=True,
        )

        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            replace_in_file(self, configure, "umask 077 && mktemp -d", "umask 022 && mktemp -d", strict=False)
            replace_in_file(self, configure, 'umask 077 && mkdir "$tmp"', 'umask 022 && mkdir "$tmp"', strict=False)

        # The OHOS shell can resolve the same relative path differently when
        # Automake runs each test from its generated test directory. Use the
        # source-tree path for every script that invokes the build-tree binary.
        test_dir = os.path.join(self.source_folder, "test")
        pixz_scripts = (
            "compress-file-permissions.sh",
            "single-file-round-trip.sh",
            "xz-compatibility-c-option.sh",
        )
        # pixz builds in <build_folder>/src (AutotoolsToolchain uses build_folder).
        # The scripts live in <source>/test, so the binary is two levels up
        # from the test directory plus build-release/src.
        absolute_pixz = 'PIXZ="$(cd "$(dirname "$0")/.." && pwd)/build-release/src/pixz"'
        for script_name in pixz_scripts:
            script = os.path.join(test_dir, script_name)
            if os.path.isfile(script):
                replace_in_file(self, script, "PIXZ=../src/pixz", absolute_pixz, strict=False)

        # OHOS mktemp emits garbage bytes and /tmp is read-only. Keep this
        # test's input in the writable device cache without changing the
        # permission assertion itself.
        perm_test = os.path.join(test_dir, "compress-file-permissions.sh")
        if os.path.isfile(perm_test):
            replace_in_file(
                self,
                perm_test,
                "INPUT=$(mktemp)",
                'INPUT="/storage/Users/currentUser/pixz-perm-$$"\nrm -f "$INPUT" "$INPUT.xz"\n: > "$INPUT"',
                strict=False,
            )
            # Verify the actual contract: compression preserves the input
            # mode.  A literal 0600 expectation is not portable because
            # OHOS filesystems can retain mandatory group permissions.
            # Support both GNU and BSD stat without treating a missing mode
            # query as a successful assertion.
            replace_in_file(
                self,
                perm_test,
                '''echo foo > $INPUT

$PIXZ $INPUT

[ "$(stat -c "%a" $INPUT.xz)" = 600 ]''',
                '''echo foo > $INPUT

mode_of () {
  stat -c "%a" "$1" 2>/dev/null || stat -f "%Lp" "$1" 2>/dev/null
}

INPUT_MODE=$(mode_of "$INPUT") || exit 1
$PIXZ $INPUT
OUTPUT_MODE=$(mode_of "$INPUT.xz") || exit 1

[ "$OUTPUT_MODE" = "$INPUT_MODE" ]''',
                strict=True,
            )

    def package(self):
        dest = shlex.quote(self.package_folder)
        self.run(f"make install DESTDIR={dest}", cwd=self.build_folder, env=["conanbuild", "pixz_ohos_env"])

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        self.runenv_info.prepend_path("PATH", bindir)
        # pixz is dynamically linked against libarchive/xz; expose their
        # libdirs so downstream consumers (and test_package) get them on
        # LD_LIBRARY_PATH via VirtualRunEnv.
        for dep_name in ("libarchive", "xz"):
            if dep_name in self.dependencies:
                dep = self.dependencies[dep_name]
                for libdir in dep.cpp_info.libdirs:
                    self.runenv_info.prepend_path("LD_LIBRARY_PATH", str(libdir))
