"""pslib 0.4.8 for OpenHarmony PC."""

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PslibConan(ConanFile):
    name = "pslib"
    version = "0.4.8"
    description = "C library for generating PostScript documents"
    # Upstream ships GPL-2 COPYING while core sources explicitly say LGPL-2+.
    license = "GPL-2.0-or-later AND LGPL-2.0-or-later"
    homepage = "https://pslib.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libpng/1.6.58.3")
        self.requires("libjpeg/10")

    def build_requirements(self):
        self.tool_requires("intltool/0.51.0")
        self.tool_requires("gettext/0.22.5.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("PSLIB_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ValueError("PSLIB_SOURCE_ARCHIVE must name a regular file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--with-png=" + self.dependencies["libpng"].package_folder,
                "--with-jpeg=" + self.dependencies["libjpeg"].package_folder,
                "--with-gif=no",
                "--with-tiff=no",
                "--disable-nls",
            ]
        )
        tc.generate()
        AutotoolsDeps(self).generate()

    def _dependency_run_environment(self):
        environment = Environment()
        temporary = Path(self.build_folder, "configure-tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment.define("TMPDIR", str(temporary))
        wrapper_dir = getattr(self, "_intltool_wrapper_dir", None)
        if wrapper_dir:
            environment.prepend_path("PATH", str(wrapper_dir))
            for name, variable in (
                ("intltool-update", "INTLTOOL_UPDATE"),
                ("intltool-merge", "INTLTOOL_MERGE"),
                ("intltool-extract", "INTLTOOL_EXTRACT"),
            ):
                environment.define(variable, str(wrapper_dir / name))
        for dependency in (*self.dependencies.host.values(),
                           *self.dependencies.build.values()):
            if not dependency.package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs:
                directory = Path(libdir)
                if not directory.is_absolute():
                    directory = Path(dependency.package_folder, libdir)
                if directory.is_dir():
                    environment.prepend_path("LD_LIBRARY_PATH", str(directory))
        return environment

    def build(self):
        configure_args = []
        if str(self.settings.os) == "OHOS":
            # The published intltool package has a stale absolute Perl
            # shebang. Keep its package immutable and route only this build
            # through wrappers using the Perl actually installed on device.
            perl = shutil.which("perl")
            if not perl or not Path(perl).is_file():
                raise ConanInvalidConfiguration("Perl required by intltool is absent")
            intltool_bin = Path(self.dependencies.build["intltool"].package_folder, "bin")
            wrappers = Path(self.build_folder, "intltool-wrapper")
            wrappers.mkdir(exist_ok=True)
            for name in ("intltool-update", "intltool-merge", "intltool-extract"):
                original = intltool_bin / name
                if not original.is_file():
                    raise ConanInvalidConfiguration("missing intltool executable: " + name)
                wrapper = wrappers / name
                wrapper.write_text(
                    "#!/bin/sh\nexec " + shlex.quote(perl) + " "
                    + shlex.quote(str(original)) + ' "$@"\n', encoding="utf-8"
                )
                wrapper.chmod(0o755)
            self._intltool_wrapper_dir = wrappers
            # The bundled 2022 config.sub rejects a compiler's linux-ohos
            # tuple. Accept that tuple without pretending to target glibc.
            config_sub = Path(self.source_folder, "config.sub")
            content = config_sub.read_text(encoding="utf-8")
            replacements = {
                "gnu* | android* | bsd* |": "gnu* | android* | ohos* | bsd* |",
                "linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* \\":
                    "linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* | linux-ohos* \\",
            }
            for old, new in replacements.items():
                if content.count(old) != 1:
                    raise ConanInvalidConfiguration(
                        "unexpected upstream config.sub OS table"
                    )
                content = content.replace(old, new, 1)
            config_sub.write_text(content, encoding="utf-8")

            # The generated intltool macro requires XML::Parser even when
            # translations are disabled. The available prebuilt XS module
            # targets an older Perl ABI; the all-no po target never uses it.
            configure = Path(self.source_folder, "configure")
            script = configure.read_text(encoding="utf-8")
            old_xml_check = 'if test "x" != "xno-xml"; then'
            if script.count(old_xml_check) != 1:
                raise ConanInvalidConfiguration("unexpected intltool XML check")
            script = script.replace(
                old_xml_check, 'if test "$USE_NLS" = "yes"; then', 1
            )
            # CI's HMDFS maps the owner of 0700 Autoconf temp directories
            # away from the build uid; mktemp -d always creates 0700 even
            # when umask is relaxed. Use an atomic, unique mkdir whose mode
            # is group-accessible at creation time, never chmod afterward.
            old_temp = '''{
  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
  test -d "$tmp"
}  ||
{
  tmp=./conf$$-$RANDOM
  (umask 077 && mkdir "$tmp")
} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5'''
            new_temp = '''{
  tmp=./conf$$-$RANDOM
  (umask 007 && mkdir "$tmp")
} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5'''
            if script.count(old_temp) != 1:
                raise ConanInvalidConfiguration(
                    "unexpected config.status temporary-directory logic"
                )
            script = script.replace(old_temp, new_temp, 1)
            configure.write_text(script, encoding="utf-8")

            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            compiler = executables.get("c")
            if not compiler or not Path(compiler).is_file():
                raise ConanInvalidConfiguration("missing configured C compiler")
            result = subprocess.run(
                [compiler, "-dumpmachine"], capture_output=True, text=True,
                check=True, timeout=10,
            )
            triplet = result.stdout.strip()
            if not re.fullmatch(r"[A-Za-z0-9_.+-]+", triplet):
                raise ConanInvalidConfiguration("invalid compiler target triplet")
            configure_args = ["--build=" + triplet, "--host=" + triplet]
        with self._dependency_run_environment().vars(self).apply():
            autotools = Autotools(self)
            autotools.configure(args=configure_args)
            config_header = Path(self.build_folder, "config.h")
            if not config_header.is_file():
                raise ConanInvalidConfiguration("configure did not generate config.h")
            feature_defines = config_header.read_text(encoding="utf-8")
            for feature in ("HAVE_LIBPNG", "HAVE_LIBJPEG"):
                if not re.search(r"^#define " + feature + r" 1$", feature_defines, re.M):
                    raise ConanInvalidConfiguration(
                        "requested image codec was not enabled: " + feature
                    )
            autotools.make(args=["-j2"])
            # The 0.4.8 release registers no upstream tests, but keep the
            # upstream check target in the build and report its actual result.
            autotools.make(target="check", args=["-j1"])

    def package(self):
        with self._dependency_run_environment().vars(self).apply():
            Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        pc = Path(self.package_folder, "lib", "pkgconfig", "libps.pc")
        if not pc.is_file():
            raise ValueError("pslib did not install libps.pc")
        contents = pc.read_text(encoding="utf-8")
        lines = contents.splitlines()
        prefixes = [i for i, line in enumerate(lines) if line.startswith("prefix=")]
        requirements = [i for i, line in enumerate(lines) if line.startswith("Requires:")]
        if len(prefixes) != 1 or len(requirements) != 1:
            raise ValueError("unexpected upstream libps.pc fields")
        lines[prefixes[0]] = "prefix=${pcfiledir}/../.."
        lines[requirements[0]] = "Requires.private: libpng libjpeg"
        pc.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def package_info(self):
        self.cpp_info.libs = ["ps"]
        self.cpp_info.set_property("cmake_file_name", "pslib")
        self.cpp_info.set_property("cmake_target_name", "pslib::pslib")
        self.cpp_info.set_property("pkg_config_name", "libps")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
