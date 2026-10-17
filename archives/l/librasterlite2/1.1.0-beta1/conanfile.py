#!/usr/bin/env python3
"""Conan recipe for the RasterLite2 1.1.0-beta1 pre-release."""

import glob
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import load_toolchain_args
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class Librasterlite2Conan(ConanFile):
    name = "librasterlite2"
    version = "1.1.0-beta1"
    description = "Raster coverage storage and retrieval library backed by SpatiaLite"
    license = "MPL-1.1 OR GPL-2.0-or-later OR LGPL-2.1-or-later"
    homepage = "https://www.gaia-gis.it/fossil/librasterlite2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("sqlite3/3.49.1")
        self.requires("zlib/1.3.1.1")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("giflib/5.2.2")
        self.requires("libtiff/4.7.2")
        self.requires("libgeotiff/1.7.4")
        self.requires("proj/9.3.1.1")
        self.requires("openjpeg2/2.5.4")
        self.requires("libwebp/1.6.0")
        self.requires("xz/5.6.2")
        self.requires("lz4/1.10.0")
        self.requires("zstd/1.5.7")
        self.requires("libspatialite/5.1.0.2")
        self.requires("libpng/1.6.58")
        self.requires("curl/8.15.0")
        self.requires("libxml2/2.15.3")
        self.requires("minizip/1.3.1")
        self.requires("freetype/2.14.3")
        # Match the exact fontconfig closure published for cairo/1.18.4.
        self.requires("fontconfig/2.18.1.1")
        self.requires("pixman/0.46.4")
        self.requires("cairo/1.18.4")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        source = dict(self.conan_data["sources"])
        source_archive = os.getenv("LIBRASTERLITE2_SOURCE_ARCHIVE")
        if source_archive:
            archive_path = Path(source_archive).expanduser().resolve()
            if not archive_path.is_file():
                raise ConanInvalidConfiguration(
                    "LIBRASTERLITE2_SOURCE_ARCHIVE is not a regular file: {}".format(
                        archive_path
                    )
                )
            source["url"] = archive_path.as_uri()
            source["filename"] = "librasterlite2-1.1.0-beta1.tar.gz"
        get(self, **source, strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        self._write_pkg_config_compat()
        if str(self.settings.os) == "OHOS":
            self._write_configure_compiler_wrapper()
        toolchain = AutotoolsToolchain(self)
        # AArch64 defaults plain char to unsigned, while upstream uses it for INT8.
        toolchain.extra_cflags.append("-fsigned-char")
        toolchain.configure_args.extend(["--enable-gcov=no"])
        if self.options.shared:
            toolchain.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            toolchain.configure_args.extend(["--disable-shared", "--enable-static"])
        toolchain.generate()

    def _write_pkg_config_compat(self):
        """Expose real Conan libraries whose recipes omit a pkg-config file."""
        dependency = self.dependencies["lz4"]
        package_folder = dependency.package_folder
        if not package_folder:
            return
        library = os.path.join(package_folder, "lib", "liblz4.a")
        if not os.path.isfile(library):
            raise ConanInvalidConfiguration(
                "lz4 package is missing the library required by liblz4.pc"
            )
        existing = os.path.join(package_folder, "lib", "pkgconfig", "liblz4.pc")
        if os.path.isfile(existing):
            return
        compat = os.path.join(self.generators_folder, "liblz4.pc")
        content = "\n".join(
            [
                "prefix={}".format(package_folder),
                "exec_prefix=${prefix}",
                "libdir=${prefix}/lib",
                "includedir=${prefix}/include",
                "",
                "Name: liblz4",
                "Description: LZ4 compression library",
                "Version: {}".format(dependency.ref.version),
                "Libs: -L${libdir} -llz4",
                "Cflags: -I${includedir}",
                "",
            ]
        )
        with open(compat, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    @property
    def _configure_compiler_wrapper_path(self):
        return os.path.join(self.generators_folder, "rasterlite2-clang-conftest.sh")

    @property
    def _configure_sign_events_path(self):
        return os.path.join(self.generators_folder, "rasterlite2-conftest-sign-events.txt")

    def _write_configure_compiler_wrapper(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        configured_cc = compiler_executables.get("c") if compiler_executables else None
        compiler_command = shlex.split(configured_cc) if configured_cc else []
        if len(compiler_command) != 1 or not os.path.isabs(compiler_command[0]):
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables.c must be one absolute executable path"
            )
        real_cc = os.path.realpath(compiler_command[0])
        if not os.path.isfile(real_cc):
            raise ConanInvalidConfiguration(
                "configured C compiler is missing: {}".format(real_cc)
            )
        tools = {
            "awk": "/system/bin/awk",
            "chmod": "/system/bin/chmod",
            "cp": "/system/bin/cp",
            "mv": "/system/bin/mv",
            "objcopy": "/data/service/hnp/bin/llvm-objcopy",
            "readelf": "/data/service/hnp/bin/llvm-readelf",
            "rm": "/system/bin/rm",
            "signer": "/data/service/hnp/bin/binary-sign-tool",
        }
        missing = [path for path in tools.values() if not os.path.isfile(path)]
        if missing:
            raise ConanInvalidConfiguration(
                "configure signing tools are missing: {}".format(missing)
            )
        runtime_libdirs = []
        for _ref, dependency in self.dependencies.items():
            runtime_libdirs.extend(self._absolute_libdirs(dependency))
        runtime_rpath = ":".join(dict.fromkeys(runtime_libdirs))
        if not runtime_rpath:
            raise ConanInvalidConfiguration("configure probes require dependency runtimes")

        os.makedirs(self.generators_folder, exist_ok=True)
        with open(self._configure_sign_events_path, "w", encoding="utf-8"):
            pass
        script = """#!/system/bin/sh
set -eu

real_cc=@REAL_CC@
readelf=@READELF@
signer=@SIGNER@
awk_tool=@AWK@
chmod_tool=@CHMOD@
cp_tool=@CP@
mv_tool=@MV@
objcopy=@OBJCOPY@
rm_tool=@RM@
runtime_rpath=@RUNTIME_RPATH@
events=@EVENTS@
probe_mode=${RASTERLITE2_CONFIGURE_PROBES:-0}

output=a.out
expect_output=0
compile_only=0
for argument in "$@"; do
  if [ "$expect_output" -eq 1 ]; then
    output="$argument"
    expect_output=0
    continue
  fi
  case "$argument" in
    -o) expect_output=1 ;;
    -o?*) output=${argument#-o} ;;
    -c|-E|-S) compile_only=1 ;;
  esac
done
if [ "$expect_output" -ne 0 ]; then
  printf 'RASTERLITE2_CC_MISSING_OUTPUT\n' >&2
  exit 91
fi
case "$output" in
  /*) ;;
  *) output="$(pwd)/$output" ;;
esac
name=${output##*/}
is_conftest=0
case "$name" in
  conftest*) is_conftest=1 ;;
esac

if [ "$probe_mode" -eq 1 ] && [ "$is_conftest" -eq 1 ] && [ "$compile_only" -eq 0 ]; then
  "$real_cc" "$@" "-Wl,-rpath,$runtime_rpath"
else
  "$real_cc" "$@"
fi

if [ "$probe_mode" -ne 1 ] || [ "$is_conftest" -ne 1 ] || [ "$compile_only" -ne 0 ] || [ ! -f "$output" ]; then
  exit 0
fi
elf_type=$("$readelf" -h "$output" 2>/dev/null | "$awk_tool" '$1 == "Type:" {print $2; exit}')
case "$elf_type" in
  EXEC|DYN) ;;
  *) exit 0 ;;
esac
temporary="${output}.signing-$$"
if [ -e "$temporary" ]; then
  printf 'RASTERLITE2_CC_SIGNING_TEMP_EXISTS=%s\n' "$temporary" >&2
  exit 92
fi
signing_active=1
cleanup_signing() {
  if [ "$signing_active" -eq 1 ]; then
    "$rm_tool" -f "$temporary"
  fi
}
trap cleanup_signing 0
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
"$cp_tool" "$output" "$temporary"
sections=$("$readelf" -S "$temporary")
case "$sections" in
  *".codesign"*) "$objcopy" --remove-section .codesign "$temporary" ;;
esac
"$signer" sign -inFile "$temporary" -outFile "$temporary" -selfSign 1 1>&2
signed_sections=$("$readelf" -S "$temporary")
case "$signed_sections" in
  *".codesign"*) ;;
  *)
    printf 'RASTERLITE2_CC_CODESIGN_MISSING=%s\n' "$output" >&2
    exit 93
    ;;
esac
"$chmod_tool" 755 "$temporary"
"$mv_tool" -f "$temporary" "$output"
signing_active=0
trap - 0 HUP INT TERM
printf '%s\n' "$output" >> "$events"
"""
        replacements = {
            "@REAL_CC@": real_cc,
            "@READELF@": tools["readelf"],
            "@SIGNER@": tools["signer"],
            "@AWK@": tools["awk"],
            "@CHMOD@": tools["chmod"],
            "@CP@": tools["cp"],
            "@MV@": tools["mv"],
            "@OBJCOPY@": tools["objcopy"],
            "@RM@": tools["rm"],
            "@RUNTIME_RPATH@": runtime_rpath,
            "@EVENTS@": self._configure_sign_events_path,
        }
        for marker, value in replacements.items():
            script = script.replace(marker, shlex.quote(value))
        with open(
            self._configure_compiler_wrapper_path,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(script)

    def _validate_configure_signing(self):
        if str(self.settings.os) != "OHOS":
            return
        try:
            with open(self._configure_sign_events_path, encoding="utf-8") as handle:
                events = [line.strip() for line in handle if line.strip()]
        except OSError as error:
            raise ConanInvalidConfiguration(
                "configure conftest signing evidence is missing"
            ) from error
        if not any(os.path.basename(path).startswith("conftest") for path in events):
            raise ConanInvalidConfiguration("configure produced no signed conftest executable")

    @staticmethod
    def _absolute_libdirs(dependency):
        """Return dependency library directories as paths usable at runtime."""
        package_folder = dependency.package_folder
        for libdir in dependency.cpp_info.libdirs:
            if os.path.isabs(libdir):
                yield os.path.normpath(libdir)
            elif package_folder:
                yield os.path.normpath(os.path.join(package_folder, libdir))

    def _environment(self, include_dependency_runtime=True):
        env = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        env.define("TMPPREFIX", os.path.join(tmpdir, "zsh-tmp-"))
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # Some OHOS dependency recipes ship canonical .pc files in their package
        # lib/pkgconfig directories without exporting that directory through
        # Conan's generated dependency metadata.
        for _ref, dependency in self.dependencies.items():
            package_folder = dependency.package_folder
            if not package_folder:
                continue
            package_pkgconfig = os.path.join(package_folder, "lib", "pkgconfig")
            if os.path.isdir(package_pkgconfig):
                env.prepend_path("PKG_CONFIG_PATH", package_pkgconfig)
        if str(self.settings.os) == "OHOS":
            env.define("MKDIR_P", "/system/bin/mkdir -p")
            env.define("CONFIG_SHELL", "/system/bin/sh")
            env.define("SHELL", "/system/bin/sh")
            env.define("CONFIG_GUESS_USE_CC_DUMPMACHINE", "1")
            env.prepend_path("PATH", "/data/service/hnp/bin")
        if include_dependency_runtime:
            for _ref, dependency in self.dependencies.items():
                for libdir in self._absolute_libdirs(dependency):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        proj_data = os.path.join(self.dependencies["proj"].package_folder, "share", "proj")
        if not os.path.isfile(os.path.join(proj_data, "proj.db")):
            raise ConanInvalidConfiguration("proj package is missing share/proj/proj.db")
        env.define("PROJ_DATA", proj_data)
        return env

    def _make_overrides(self):
        if str(self.settings.os) != "OHOS" or not self.options.shared:
            return []
        return [
            'librasterlite2_la_LDFLAGS="-avoid-version -no-undefined"',
            'mod_rasterlite2_la_LDFLAGS="-module -avoid-version -no-undefined"',
        ]

    def _configure(self, autotools):
        if str(self.settings.os) != "OHOS":
            autotools.configure()
            return
        shell = "/system/bin/sh"
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(self._configure_compiler_wrapper_path):
            raise ConanInvalidConfiguration("configure compiler wrapper was not generated")
        configure_cc = shlex.join([shell, self._configure_compiler_wrapper_path])
        configure_args = load_toolchain_args(self.generators_folder).get("configure_args", "")
        command = shlex.join([shell, configure])
        if configure_args:
            command = "{} {}".format(command, configure_args)
        command = "CONFIG_SHELL={} SHELL={} PWD={} RASTERLITE2_CONFIGURE_PROBES=1 CC={} {}".format(
            shell,
            shell,
            shlex.quote(self.build_folder),
            shlex.quote(configure_cc),
            command,
        )
        self.run(command, cwd=self.build_folder)

    def build(self):
        apply_conandata_patches(self)
        tool_env = self._environment(include_dependency_runtime=False)
        runtime_env = self._environment()
        old_umask = os.umask(0o022)
        try:
            with tool_env.vars(self).apply():
                autotools = Autotools(self)
                self._configure(autotools)
                self._validate_configure_signing()
                autotools.make(args=["-j1"] + self._make_overrides())
                # Build every test first, then sign every target ELF.
                autotools.make(
                    target="check", args=["-j1", "TESTS="] + self._make_overrides()
                )
                self._sign_tree(self.build_folder)
            with runtime_env.vars(self).apply():
                autotools.make(
                    target="check",
                    args=["-j1", 'LOG_COMPILER="/system/bin/sh"']
                    + self._make_overrides(),
                )
            self._validate_upstream_tests()
        finally:
            os.umask(old_umask)

    def _validate_upstream_tests(self):
        test_log = os.path.join(self.build_folder, "test", "test-suite.log")
        try:
            with open(test_log, encoding="utf-8", errors="strict") as handle:
                text = handle.read()
        except OSError as error:
            raise ConanInvalidConfiguration(
                "Automake test summary is missing: {}".format(test_log)
            ) from error
        summary = {}
        for key in ("TOTAL", "PASS", "SKIP", "XFAIL", "FAIL", "XPASS", "ERROR"):
            match = re.search(r"^# {}:\s+(\d+)\s*$".format(key), text, re.MULTILINE)
            if match is None:
                raise ConanInvalidConfiguration(
                    "Automake test summary is missing {}".format(key)
                )
            summary[key] = int(match.group(1))
        if summary["TOTAL"] != 71 or summary["PASS"] != 71:
            raise ConanInvalidConfiguration(
                "unexpected Automake test total: {}".format(summary)
            )
        unexpected = {
            key: summary[key]
            for key in ("SKIP", "XFAIL", "FAIL", "XPASS", "ERROR")
            if summary[key]
        }
        if unexpected:
            raise ConanInvalidConfiguration(
                "upstream tests did not all pass: {}".format(unexpected)
            )
        self.output.info("LIBRASTERLITE2_UPSTREAM_TESTS=71/71")

    def package(self):
        env = self._environment(include_dependency_runtime=False)
        old_umask = os.umask(0o022)
        try:
            with env.vars(self).apply():
                Autotools(self).install(args=self._make_overrides())
            copy(
                self,
                "COPYING",
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
            )
            self._sign_tree(self.package_folder)
            self._validate_package_layout()
        finally:
            os.umask(old_umask)

    def _validate_package_layout(self):
        include_dir = os.path.join(self.package_folder, "include", "rasterlite2")
        if not os.path.isdir(include_dir):
            raise ConanInvalidConfiguration("missing rasterlite2 public headers")
        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            expected = ["librasterlite2.so", "mod_rasterlite2.so"]
            missing = [name for name in expected if not os.path.isfile(os.path.join(libdir, name))]
            if missing:
                raise ConanInvalidConfiguration("missing shared artifacts: {}".format(", ".join(missing)))
            aliases = glob.glob(os.path.join(libdir, "librasterlite2.so.*"))
            aliases += glob.glob(os.path.join(libdir, "mod_rasterlite2.so.*"))
            if str(self.settings.os) == "OHOS" and aliases:
                raise ConanInvalidConfiguration("versioned HMDFS aliases are forbidden: {}".format(aliases))
        elif not os.path.isfile(os.path.join(libdir, "librasterlite2.a")):
            raise ConanInvalidConfiguration("missing static librasterlite2.a")

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_tree(self, root):
        if str(self.settings.os) != "OHOS":
            return
        for directory, _subdirs, filenames in os.walk(root):
            for filename in filenames:
                path = os.path.join(directory, filename)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                if os.access(path, os.X_OK) or ".so" in filename:
                    self._sign_elf(path)

    def _sign_elf(self, path):
        path = Path(path)
        if not path.is_file():
            raise ConanInvalidConfiguration(
                "required OHOS ELF is missing: {}".format(path)
            )
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        readelf = "/data/service/hnp/bin/llvm-readelf"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if any(not os.path.isfile(tool) for tool in (objcopy, readelf, signer)):
            raise ConanInvalidConfiguration("OHOS ELF signing tools are required")
        temporary = path.with_name("{}.signing-{}".format(path.name, os.getpid()))
        if os.path.lexists(temporary):
            raise ConanInvalidConfiguration(
                "OHOS ELF signing temporary already exists: {}".format(temporary)
            )
        try:
            shutil.copy2(path, temporary)
            sections = subprocess.run(
                [readelf, "-S", str(temporary)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            if ".codesign" in sections:
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", str(temporary)],
                    check=True,
                )
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    str(temporary),
                    "-outFile",
                    str(temporary),
                    "-selfSign",
                    "1",
                ],
                check=True,
            )
            signed_sections = subprocess.run(
                [readelf, "-S", str(temporary)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            if ".codesign" not in signed_sections:
                raise ConanException("signer did not add .codesign: {}".format(path))
            os.replace(temporary, path)
        finally:
            if os.path.lexists(temporary):
                os.unlink(temporary)

    def package_info(self):
        self.cpp_info.libs = ["rasterlite2"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = [
            "sqlite3::sqlite3", "zlib::zlib", "libjpeg-turbo::libjpeg-turbo",
            "giflib::giflib", "libtiff::libtiff", "libgeotiff::libgeotiff",
            "proj::proj", "openjpeg2::openjpeg2", "libwebp::libwebp", "xz::xz",
            "lz4::lz4", "zstd::zstd", "libspatialite::libspatialite",
            "libpng::libpng", "curl::libcurl", "libxml2::libxml2",
            "minizip::minizip", "freetype::freetype", "fontconfig::fontconfig",
            "pixman::pixman", "cairo::cairo",
        ]
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
        self.cpp_info.set_property("cmake_file_name", "RasterLite2")
        self.cpp_info.set_property("cmake_target_name", "RasterLite2::RasterLite2")
        self.cpp_info.set_property("pkg_config_name", "rasterlite2")
        # Propagate shared dependency directories to direct consumers. Conan's
        # VirtualRunEnv does not infer transitive libdirs from cpp_info.requires.
        for _ref, dependency in self.dependencies.items():
            for libdir in self._absolute_libdirs(dependency):
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", libdir)
        proj_data = os.path.join(self.dependencies["proj"].package_folder, "share", "proj")
        if os.path.isdir(proj_data):
            self.runenv_info.define_path("PROJ_DATA", proj_data)
            self.buildenv_info.define_path("PROJ_DATA", proj_data)
