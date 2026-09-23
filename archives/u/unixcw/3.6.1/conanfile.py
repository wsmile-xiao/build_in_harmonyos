#!/usr/bin/env python3
"""Conan recipe for unixcw 3.6.1 — OHOS (OpenHarmony) aarch64 adaptation.

unixcw is a Morse code (CW) library producing libcw.so / libcw.pc.
Build system: Autotools (non-recursive automake, ships generated configure).
Portability patches: config.guess/config.sub OHOS triplet recognition (E007),
libtool version-flag override (HMDFS unversioned output), non-fatal
textdomain probe (OHOS libc lacks textdomain; i18n degrades gracefully).
Optional components xcwcp (Qt5), cwcp (ncurses), pulseaudio/oss/console
backends are disabled at configure time.
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UnixcwConan(ConanFile):
    name = "unixcw"
    version = "3.6.1"
    description = "Morse code (CW) library and tools"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/unixcw/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"unixcw supports Linux and OHOS, not {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # ALSA is the retained audio backend (alsa-lib/1.2.16.1, OHOS-adapted).
        self.requires("alsa-lib/1.2.16.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"][str(self.version)]
        archive = os.path.join(self.source_folder, "unixcw-3.6.1.orig.tar.gz")
        get(self, url=source["url"], sha256=source["sha256"], strip_root=True)
        if os.path.isfile(archive):
            os.unlink(archive)

    def generate(self):
        VirtualBuildEnv(self).generate()

        temp_dir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(temp_dir, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", temp_dir)
        if str(self.settings.os) == "OHOS":
            environment.define_path("CONFIG_SHELL", "/system/bin/sh")
            environment.define_path("SHELL", "/system/bin/sh")
            # OHOS SDK ships a placeholder libintl.h that declares no
            # textdomain/gettext; forcing the probe to "no" makes i18n.c
            # take its graceful no-gettext path (configure.ac probe is
            # already non-fatal via patch 0004).
            environment.define("ac_cv_header_libintl_h", "no")
            # OHOS: configure runs compiled conftest binaries during probes;
            # dependency shared libs (alsa-lib) must be on the loader path.
            for dependency in self.dependencies.values():
                for libdir in dependency.cpp_info.libdirs:
                    full = os.path.join(dependency.package_folder, libdir)
                    if os.path.isdir(full):
                        environment.prepend_path("LD_LIBRARY_PATH", full)
        environment.vars(self).save_script("unixcw_build_env")

        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            (
                "--disable-xcwcp",      # Qt5 GUI, not needed
                "--disable-cwcp",       # needs -lcurses, disabled to keep deps minimal
                "--disable-pulseaudio", # PulseAudio backend not needed
                "--disable-oss",        # no OSS on OHOS
                "--disable-console",    # no console buzzer on OHOS
                "--disable-silent-rules",
            )
        )
        toolchain.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)

        if str(self.settings.os) == "OHOS":
            # E002/HMDFS: autoconf tmp dirs created with umask 077 fail on OHOS
            # because config.status cannot execute inside them.
            configure_path = os.path.join(self.source_folder, "configure")
            replace_in_file(
                self, configure_path, "umask 077", "umask 022", strict=False
            )

        autotools = Autotools(self)
        autotools.configure()
        # 0003/0004 patches touch configure.ac / Makefile.am, so automake
        # wants to re-run aclocal/automake (unavailable in the OHOS env).
        # Refresh the mtimes of every generated file in the source copy so
        # make proceeds with the shipped generated inputs.
        self._refresh_generated_build_files(self.source_folder)
        autotools.make(args=self._make_args())
        # ── upstream official tests (layer 1) ──
        autotools.make(target="check", args=self._check_args())

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=self._make_args())
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        self._make_pkg_config_relocatable("libcw.pc")

    def package_info(self):
        self.cpp_info.libs = ["cw"]
        self.cpp_info.set_property("cmake_file_name", "libcw")
        self.cpp_info.set_property("cmake_target_name", "libcw::libcw")
        self.cpp_info.set_property("pkg_config_name", "libcw")

    # ---- helpers ----------------------------------------------------------

    @staticmethod
    def _refresh_generated_build_files(work_dir):
        generated = (
            "aclocal.m4",
            "configure",
            "config.h.in",
            "config.status",
            "Makefile.in",
            "src/Makefile.in",
            "src/libcw/Makefile.in",
            "src/libcw/tests/Makefile.in",
            "src/cwutils/Makefile.in",
            "src/cwutils/lib/Makefile.in",
            "src/test_framework/Makefile.in",
            "src/test_framework/basic_utils/Makefile.in",
            "src/cwgen/Makefile.in",
            "src/cw/Makefile.in",
        )
        for relative in generated:
            path = os.path.join(work_dir, relative)
            if os.path.isfile(path):
                os.utime(path, None)

    def _make_args(self):
        arguments = ["-j1"]
        if (
            str(self.settings.os) == "OHOS"
            and str(self.options.shared).lower() == "true"
        ):
            # HMDFS: unversioned output avoids .so -> .so.8 symlink chains
            # (same convention as alsa-lib on OHOS).
            arguments.append("LIBCW_LIBTOOL_VERSION_FLAGS=-avoid-version")
        return arguments

    def _check_args(self):
        arguments = self._make_args()
        if str(self.settings.os) == "OHOS":
            # E228: extensionless libtool test wrappers cannot execute on HMDFS.
            # Route every test entry through /system/bin/sh + a launcher that
            # applies an external timeout to both scripts and ELF binaries.
            launcher = self._write_upstream_test_launcher()
            arguments.extend(
                (
                    "LOG_COMPILER=/system/bin/sh",
                    # Quote the whole value so make keeps "launcher 180" as a
                    # single AM_LOG_FLAGS assignment (two args for the launcher).
                    shlex.quote(f"AM_LOG_FLAGS={launcher} 180"),
                )
            )
        return arguments

    def _write_upstream_test_launcher(self):
        launcher = os.path.join(self.build_folder, "conan", "unixcw-test-launcher.sh")
        os.makedirs(os.path.dirname(launcher), exist_ok=True)
        with open(launcher, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#!/system/bin/sh\n"
                "set -eu\n"
                'test "$#" -ge 2\n'
                "seconds=$1\n"
                "executable=$2\n"
                "shift 2\n"
                # ELF magic 0x7f 'E' 'L' 'F': run the binary directly.
                # Everything else (shebang scripts and extensionless scripts
                # such as greptest.sh) goes through /system/bin/sh.
                'magic=$(dd if="$executable" bs=1 count=4 2>/dev/null || true)\n'
                'if [ "$magic" = "$(printf \'\\177ELF\')" ]; then\n'
                '  exec /system/bin/timeout "$seconds" "$executable" "$@"\n'
                "fi\n"
                'exec /system/bin/timeout "$seconds" /system/bin/sh "$executable" "$@"\n'
            )
        os.chmod(launcher, 0o755)
        return launcher

    def _make_pkg_config_relocatable(self, name):
        path = os.path.join(self.package_folder, "lib", "pkgconfig", name)
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(
                f"upstream install did not produce {name}"
            )
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        prefix_lines = [
            index for index, line in enumerate(lines) if line.startswith("prefix=")
        ]
        if len(prefix_lines) > 1:
            raise ConanInvalidConfiguration(
                f"{name} contains multiple prefix assignments"
            )
        if prefix_lines:
            lines[prefix_lines[0]] = "prefix=${pcfiledir}/../.."
        else:
            lines[0:0] = [
                "prefix=${pcfiledir}/../..",
                "exec_prefix=${prefix}",
            ]
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")
