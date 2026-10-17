#!/usr/bin/env python3
"""Conan recipe for libspatialite 5.1.0.1.

The package version carries the first OpenHarmony recipe revision for upstream
libspatialite 5.1.0. GEOS, RTTOPO, PROJ, libxml2 and GeoPackage support stay
enabled because they are part of the spatialite-gui consumer contract.
"""

import glob
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import load_toolchain_args
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout


class LibspatialiteConan(ConanFile):
    name = "libspatialite"
    version = "5.1.0.1"
    description = "SQLite spatial extension with OGC geometry support"
    license = "MPL-1.1 OR GPL-2.0-or-later OR LGPL-2.1-or-later"
    homepage = "https://www.gaia-gis.it/fossil/libspatialite"
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
        self.requires("proj/9.3.1.1")
        # libspatialite directly uses GEOS; librttopo resolves the same exact
        # GEOS revision, so the public dependency graph has one ABI contract.
        self.requires("geos/3.13.1")
        self.requires("librttopo/1.1.0.1")
        self.requires("libxml2/2.15.3")

    def layout(self):
        basic_layout(self)
        # The release tarball contains generated gaiaconfig.h files. A VPATH
        # build lets those stale x86_64 headers shadow configure's OHOS output.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

        if str(self.settings.os) == "OHOS":
            self._write_configure_compiler_wrapper()

        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                "--enable-mathsql",
                "--enable-proj",
                "--enable-iconv",
                "--disable-freexl",
                "--enable-epsg",
                "--enable-geos",
                "--enable-gcp",
                "--enable-geosadvanced",
                "--enable-geosreentrant",
                "--enable-geos370",
                "--enable-geos3100",
                "--enable-geos3110",
                "--enable-rttopo",
                "--enable-libxml2",
                "--disable-minizip",
                "--enable-geopackage",
                "--disable-examples",
                "--with-geosconfig={}".format(self._geos_config_path),
            ]
        )
        if self.options.shared:
            toolchain.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            toolchain.configure_args.extend(["--disable-shared", "--enable-static"])
        toolchain.generate()

    @property
    def _geos_config_path(self):
        return os.path.join(self.build_folder, "geos-config-ohos")

    @property
    def _configure_compiler_wrapper_path(self):
        return os.path.join(self.generators_folder, "spatialite-clang-conftest.sh")

    @property
    def _configure_sign_events_path(self):
        return os.path.join(self.generators_folder, "spatialite-conftest-sign-events.txt")

    def _write_configure_compiler_wrapper(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        real_cc = compiler_executables.get("c", "clang") if compiler_executables else "clang"
        tools = {
            "awk": "/system/bin/awk",
            "chmod": "/system/bin/chmod",
            "readelf": "/data/service/hnp/bin/llvm-readelf",
            "signer": "/data/service/hnp/bin/binary-sign-tool",
        }
        missing = [path for path in tools.values() if not os.path.isfile(path)]
        if missing:
            raise ConanInvalidConfiguration(
                "OHOS configure signing tools are missing: {}".format(missing)
            )

        runtime_libdirs = []
        for _ref, dependency in self.dependencies.items():
            runtime_libdirs.extend(dependency.cpp_info.libdirs)
        runtime_rpath = ":".join(dict.fromkeys(runtime_libdirs))
        if not runtime_rpath:
            raise ConanInvalidConfiguration(
                "OHOS configure probes require dependency runtime directories"
            )

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
runtime_rpath=@RUNTIME_RPATH@
events=@EVENTS@
probe_mode=${SPATIALITE_CONFIGURE_PROBES:-0}

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
  printf 'SPATIALITE_CC_MISSING_OUTPUT\n' >&2
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
"$signer" sign -inFile "$output" -outFile "$output" -selfSign 1
"$chmod_tool" 755 "$output"
printf '%s\n' "$output" >> "$events"
"""
        replacements = {
            "@REAL_CC@": real_cc,
            "@READELF@": tools["readelf"],
            "@SIGNER@": tools["signer"],
            "@AWK@": tools["awk"],
            "@CHMOD@": tools["chmod"],
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
            raise ConanInvalidConfiguration(
                "configure produced no signed conftest executable"
            )

    def _write_geos_config(self):
        """Build a signed geos-config replacement from Conan metadata.

        The GEOS package exposes CMake/pkg-config metadata. libspatialite 5.1.0
        insists on executing geos-config, while HMDFS cannot reliably execute
        package-cache shell scripts. A tiny ELF helper keeps the upstream
        configure contract without hard-coded machine paths.
        """
        geos = self.dependencies["geos"].cpp_info
        if not geos.includedirs or not geos.libdirs:
            raise ConanInvalidConfiguration("geos package has no include/lib directories")

        def c_string(value):
            return value.replace("\\", "\\\\").replace('"', '\\"')

        include_dir = c_string(geos.includedirs[0])
        lib_dir = c_string(geos.libdirs[0])
        source = os.path.join(self.build_folder, "geos-config-ohos.c")
        os.makedirs(self.build_folder, exist_ok=True)
        with open(source, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#include <stdio.h>\n"
                "#include <string.h>\n"
                "int main(int argc, char **argv) {\n"
                "  if (argc != 2) return 2;\n"
                '  if (!strcmp(argv[1], "--includes")) { puts("%s"); return 0; }\n'
                '  if (!strcmp(argv[1], "--ldflags")) { puts("-L%s"); return 0; }\n'
                '  if (!strcmp(argv[1], "--cflags")) { puts("-I%s"); return 0; }\n'
                '  if (!strcmp(argv[1], "--clibs")) { puts("-lgeos_c"); return 0; }\n'
                '  if (!strcmp(argv[1], "--version")) { puts("3.13.1"); return 0; }\n'
                "  return 2;\n"
                "}\n" % (include_dir, lib_dir, include_dir)
            )

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c", "clang") if compiler_executables else "clang"
        self.run('"{}" "{}" -O2 -o "{}"'.format(cc, source, self._geos_config_path))
        self._sign_elf(self._geos_config_path, required=str(self.settings.os) == "OHOS")

    def _build_environment(self, include_dependency_runtime=True):
        env = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        env.define("TMPPREFIX", tmpdir)
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)

        if str(self.settings.os) == "OHOS":
            env.define("MKDIR_P", "/system/bin/mkdir -p")
            env.define("CONFIG_SHELL", "/system/bin/sh")
            env.define("SHELL", "/system/bin/sh")
            env.prepend_path("PATH", "/data/service/hnp/bin")

        if include_dependency_runtime:
            for _ref, dependency in self.dependencies.items():
                for bindir in dependency.cpp_info.bindirs:
                    env.prepend_path("PATH", bindir)
                for libdir in dependency.cpp_info.libdirs:
                    env.prepend_path("LD_LIBRARY_PATH", libdir)

        proj_data = os.path.join(
            self.dependencies["proj"].package_folder, "share", "proj"
        )
        if not os.path.isfile(os.path.join(proj_data, "proj.db")):
            raise ConanInvalidConfiguration("proj package is missing share/proj/proj.db")
        env.define("PROJ_DATA", proj_data)
        return env

    def _make_overrides(self):
        if str(self.settings.os) != "OHOS" or not self.options.shared:
            return []
        # HMDFS may copy every Libtool version alias as a full ELF. One real,
        # unversioned shared object also gives consumers a stable SONAME.
        return [
            'libspatialite_la_LDFLAGS="-avoid-version -no-undefined"',
            'mod_spatialite_la_LDFLAGS="-module -avoid-version -no-undefined"',
        ]

    def _configure(self, autotools):
        if str(self.settings.os) != "OHOS":
            autotools.configure()
            return

        # HMDFS denies direct execution of shell scripts even when their mode
        # is executable. The system shell can also resolve Conan's build cwd,
        # unlike an external Bash under HMDFS's restricted parent traversal.
        shell = "/system/bin/sh"
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(self._configure_compiler_wrapper_path):
            raise ConanInvalidConfiguration(
                "OHOS configure compiler wrapper was not generated"
            )
        configure_cc = shlex.join(
            [shell, self._configure_compiler_wrapper_path]
        )
        configure_args = load_toolchain_args(self.generators_folder).get(
            "configure_args", ""
        )
        command = shlex.join([shell, configure])
        if configure_args:
            command = "{} {}".format(command, configure_args)
        # self.run() activates Conan's generated build environment, which also
        # defines CC. Inline assignments must therefore select the signing
        # wrapper after that activation and before configure starts.
        command = "CONFIG_SHELL={} SHELL={} PWD={} SPATIALITE_CONFIGURE_PROBES=1 CC={} {}".format(
            shell,
            shell,
            shlex.quote(self.build_folder),
            shlex.quote(configure_cc),
            command,
        )
        self.run(command, cwd=self.build_folder)

    def build(self):
        apply_conandata_patches(self)
        tool_environment = self._build_environment(
            include_dependency_runtime=False
        )
        runtime_environment = self._build_environment()
        old_umask = os.umask(0o022)
        try:
            # Target dependency libraries must not enter the SDK tool runtime:
            # lld is a host process and cannot load target libxml2. Inject them
            # only after every target executable has been built and signed.
            with tool_environment.vars(self).apply():
                self._write_geos_config()
                autotools = Autotools(self)
                self._configure(autotools)
                self._validate_configure_signing()
                autotools.make(args=["-j1"] + self._make_overrides())

                # Build every registered upstream test without executing it,
                # sign the resulting target ELFs, then run the unmodified suite.
                autotools.make(
                    target="check",
                    args=["-j1", "TESTS="] + self._make_overrides(),
                )
                self._sign_tree(self.build_folder)

            with runtime_environment.vars(self).apply():
                autotools.make(
                    target="check",
                    args=[
                        "-j1",
                        'LOG_COMPILER="/system/bin/sh"',
                    ]
                    + self._make_overrides(),
                )
        finally:
            os.umask(old_umask)

    def package(self):
        environment = self._build_environment(
            include_dependency_runtime=False
        )
        old_umask = os.umask(0o022)
        try:
            with environment.vars(self).apply():
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
        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            expected = ["libspatialite.so", "mod_spatialite.so"]
            missing = [name for name in expected if not os.path.isfile(os.path.join(libdir, name))]
            if missing:
                raise ConanInvalidConfiguration(
                    "missing shared package artifacts: {}".format(", ".join(missing))
                )
            if str(self.settings.os) == "OHOS":
                aliases = glob.glob(os.path.join(libdir, "libspatialite.so.*"))
                aliases += glob.glob(os.path.join(libdir, "mod_spatialite.so.*"))
                if aliases:
                    raise ConanInvalidConfiguration(
                        "versioned Libtool aliases are forbidden on HMDFS: {}".format(aliases)
                    )
        elif not os.path.isfile(os.path.join(libdir, "libspatialite.a")):
            raise ConanInvalidConfiguration("missing static lib/libspatialite.a")

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
                    self._sign_elf(path, required=True)

    def _sign_elf(self, path, required=False):
        if str(self.settings.os) != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            if required:
                raise ConanInvalidConfiguration(
                    "OHOS ELF signing tools are required for native tests"
                )
            return
        self.run('"{}" --remove-section .codesign "{}"'.format(objcopy, path))
        self.run('"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(signer, path, path))

    def package_info(self):
        self.cpp_info.libs = ["spatialite"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = [
            "sqlite3::sqlite3",
            "zlib::zlib",
            "proj::proj",
            "geos::geos",
            "librttopo::librttopo",
            "libxml2::libxml2",
        ]
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
        self.cpp_info.set_property("cmake_file_name", "spatialite")
        self.cpp_info.set_property("cmake_target_name", "spatialite::spatialite")
        self.cpp_info.set_property("pkg_config_name", "spatialite")

        proj_data = os.path.join(
            self.dependencies["proj"].package_folder, "share", "proj"
        )
        if os.path.isdir(proj_data):
            self.runenv_info.define_path("PROJ_DATA", proj_data)
            self.buildenv_info.define_path("PROJ_DATA", proj_data)
