#!/usr/bin/env python3
"""Conan recipe — gpgme 1.24.0.1 (GPGME, autotools) on HarmonyOS PC (aarch64).

GPGME is a library providing easy access to GnuPG cryptographic operations.

OHOS-specific adaptations:
  1. E007 — config.guess/config.sub patched to recognize `linux-ohos`
     (patches/0001, 0002). Native build, no --build/--host.
  2. E011 — configure umask 077 -> 022 for HMDFS temp dirs (patches/0003).
  3. E027 — --disable-nls: published libgpg-error/1.55 is built --disable-nls,
     so we do the same (no libintl/gettext dependency required).
  4. gpgrt-config wrapper: execute libgpg-error's script through the active
     build shell instead of depending on a fixed platform shell path.
  5. E012 — libgpg-error/libassuan .pc/.la from the conan packages use
     prefix=/ (wrong absolute paths). config-overrides provides corrected
     gpg-error.pc + libassuan-config wrapper + corrected .la files, and the
     build-local la dir is prepended to LDFLAGS so libtool resolves the
     dependency .la files correctly.
  6. make -j1 (E074: OHOS SELinux forbids FIFO jobserver).
  7. Tests/ tree requires a real `gpg` binary (GnuPG runtime, not published on
     OHOS PC), so only the library subdirectories are built and installed.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GpgmeConan(ConanFile):
    name = "gpgme"
    version = "1.24.0.1"
    description = "Library providing easy access to GnuPG for cryptographic operations"
    license = "LGPL-2.1-or-later"
    homepage = "https://gnupg.org/software/gpgme/"
    url = "https://git.gnupg.org/cgi-bin/gitweb.cgi?p=gpgme.git"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires(
            "libgpg-error/1.55",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libassuan/3.0.2",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "qtbase/6.11.1.3",
            transitive_headers=True,
            transitive_libs=True,
        )

    def build_requirements(self):
        self.tool_requires("pkgconf/3.0.5")
        # Build-only runtime for the executable engine-info test.
        self.tool_requires("gnupg/2.4.9.1")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    # config-overrides: correct the dependency config scripts / .la files #
    # ------------------------------------------------------------------ #
    def _co_dir(self):
        return os.path.join(self.build_folder, "config-overrides")

    def _create_config_overrides(self):
        lgp = self.dependencies["libgpg-error"].package_folder
        las = self.dependencies["libassuan"].package_folder
        co = self._co_dir()
        for d in ("bin", "lib/pkgconfig"):
            os.makedirs(os.path.join(co, d), exist_ok=True)

        # 1) gpgrt-config wrapper: avoid dependency package scripts that can
        # hang under the OHOS shell. GPGME uses gpgrt-config for both
        # gpg-error and libassuan checks.
        with open(os.path.join(co, "bin", "gpgrt-config"), "w") as f:
            f.write(
                "#!/bin/sh\n"
                "target=gpg-error\n"
                "op=version\n"
                'for arg in "$@"; do\n'
                '  case "$arg" in\n'
                "    libassuan) target=libassuan ;;\n"
                "    gpg-error) target=gpg-error ;;\n"
                "    --version|--modversion) op=version ;;\n"
                "    --api-version) op=api_version ;;\n"
                "    --host) op=host ;;\n"
                "    --prefix) op=prefix ;;\n"
                "    --libdir) op=libdir ;;\n"
                "    --cflags) op=cflags ;;\n"
                "    --libs) op=libs ;;\n"
                "  esac\n"
                "done\n"
                'case "$op:$target" in\n'
                "  version:libassuan) echo 3.0.2 ;;\n"
                "  version:*) echo 1.55 ;;\n"
                "  api_version:libassuan) echo 3 ;;\n"
                "  api_version:*) echo 1 ;;\n"
                "  host:*) echo aarch64-unknown-linux-ohos ;;\n"
                f"  prefix:libassuan) echo {las} ;;\n"
                f"  prefix:*) echo {lgp} ;;\n"
                f"  libdir:libassuan) echo {os.path.join(las, 'lib')} ;;\n"
                f"  libdir:*) echo {os.path.join(lgp, 'lib')} ;;\n"
                f"  cflags:libassuan) echo -I{os.path.join(las, 'include')} ;;\n"
                f"  cflags:*) echo -I{os.path.join(lgp, 'include')} ;;\n"
                f"  libs:libassuan) echo -L{os.path.join(las, 'lib')} -lassuan "
                f"-L{os.path.join(lgp, 'lib')} -lgpg-error -lpthread ;;\n"
                f"  libs:*) echo -L{os.path.join(lgp, 'lib')} -lgpg-error ;;\n"
                "  *) echo 1.55 ;;\n"
                "esac\n"
            )
        os.chmod(os.path.join(co, "bin", "gpgrt-config"), 0o755)

        # 2) libassuan-config wrapper: return correct flags (package .pc uses prefix=/).
        with open(os.path.join(co, "bin", "libassuan-config"), "w") as f:
            f.write(
                "#!/bin/sh\n"
                'case "$1" in\n'
                "  --version) echo 3.0.2 ;;\n"
                "  --api-version) echo 3 ;;\n"
                "  --host) echo aarch64-unknown-linux-ohos ;;\n"
                f"  --cflags) echo -I{os.path.join(las, 'include')} ;;\n"
                f"  --libs) echo -L{os.path.join(las, 'lib')} -lassuan "
                f"-L{os.path.join(lgp, 'lib')} -lgpg-error ;;\n"
                "  *) echo 3.0.2 ;;\n"
                "esac\n"
            )
        os.chmod(os.path.join(co, "bin", "libassuan-config"), 0o755)

        # 3) corrected gpg-error.pc (package .pc uses prefix=/ -> /lib, /include).
        pc_src = os.path.join(lgp, "lib", "pkgconfig", "gpg-error.pc")
        pc_dst = os.path.join(co, "lib", "pkgconfig", "gpg-error.pc")
        with open(pc_src, "r", encoding="utf-8") as f:
            text = f.read()
        text = text.replace("prefix=/", "prefix={}".format(lgp), 1)
        with open(pc_dst, "w", encoding="utf-8") as f:
            f.write(text)
        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            qt_pc_dir = os.path.join(qtbase.package_folder, "lib", "pkgconfig")
            for filename in os.listdir(qt_pc_dir):
                if not filename.endswith(".pc"):
                    continue
                src = os.path.join(qt_pc_dir, filename)
                dst = os.path.join(co, "lib", "pkgconfig", filename)
                with open(src, "r", encoding="utf-8") as f:
                    pc_text = f.read()
                lines = pc_text.splitlines()
                for index, line in enumerate(lines):
                    if line.startswith("prefix="):
                        lines[index] = "prefix={}".format(qtbase.package_folder)
                        break
                with open(dst, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")

        # 4) corrected .la files so libtool resolves dependency paths correctly.
        with open(os.path.join(co, "lib", "libgpg-error.la"), "w") as f:
            f.write(
                "# libgpg-error.la - a libtool library file\n"
                "# Generated by libtool (GNU libtool) 2.4.7\n"
                "# Fixed for OHOS: correct libdir/dependency_libs to conan package paths.\n"
                "dlname='libgpg-error.so.0'\n"
                "library_names='libgpg-error.so.0.39.3 libgpg-error.so.0 libgpg-error.so'\n"
                "old_library=''\n"
                "inherited_linker_flags=''\n"
                "dependency_libs=''\n"
                "weak_library_names=''\n"
                "current=39\nage=39\nrevision=3\n"
                "installed=yes\nshouldnotlink=no\n"
                "dlopen=''\ndlpreopen=''\n"
                "libdir='{}/lib'\n".format(lgp)
            )
        with open(os.path.join(co, "lib", "libassuan.la"), "w") as f:
            f.write(
                "# libassuan.la - a libtool library file\n"
                "# Generated by libtool (GNU libtool) 2.4.2\n"
                "# Fixed for OHOS: correct libdir/dependency_libs to conan package paths.\n"
                "dlname='libassuan.so.9'\n"
                "library_names='libassuan.so.9.0.2 libassuan.so.9 libassuan.so'\n"
                "old_library=''\n"
                "inherited_linker_flags=''\n"
                "dependency_libs=' -L{}/lib -lgpg-error -lpthread'\n".format(lgp) +
                "weak_library_names=''\n"
                "current=9\nage=0\nrevision=2\n"
                "installed=yes\nshouldnotlink=no\n"
                "dlopen=''\ndlpreopen=''\n"
                "libdir='{}/lib'\n".format(las)
            )
        return co

    def _build_env(self, co):
        """Environment for configure/make/install runs (applied on top of the
        default process env; conanbuild env is NOT applied)."""
        lgp = self.dependencies["libgpg-error"].package_folder
        las = self.dependencies["libassuan"].package_folder
        env = Environment()
        shell = self._build_shell()
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)
        env.define("TMPDIR", self.build_folder)
        env.prepend_path("PATH", os.path.join(co, "bin"))
        # R33 + E001: 显式指定 CC/CXX（从 Conan toolchain 获取，避免 configure
        # 在 PATH 中探测到 gcc→clang 时链接失败——CI 环境实测
        # "checking for gcc... clang" 后 "C compiler cannot create executables"）。
        tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        if tools.get("c"):
            env.define("CC", tools["c"])
            env.prepend_path("PATH", os.path.dirname(tools["c"]))
        if tools.get("cpp"):
            env.define("CXX", tools["cpp"])
            env.prepend_path("PATH", os.path.dirname(tools["cpp"]))
        cxxflags = self.conf.get(
            "tools.build:cxxflags", default=[], check_type=list
        ) or []
        if not any(flag.startswith("-std=") for flag in cxxflags):
            cxxflags = list(cxxflags) + ["-std=c++17"]
        env.define("CXXFLAGS", " ".join(cxxflags))
        for variable, names in (
            ("LD", ("ld.lld", "ld")),
            ("AR", ("llvm-ar", "ar")),
            ("RANLIB", ("llvm-ranlib", "ranlib")),
            ("STRIP", ("llvm-strip", "strip")),
        ):
            tool = self._find_tool_near_compiler(tools, names)
            if tool:
                env.define(variable, tool)
        env.define(
            "CPPFLAGS",
            "-I{} -I{}".format(os.path.join(lgp, "include"), os.path.join(las, "include")),
        )
        env.define(
            "LDFLAGS",
            "-L{} -L{} -L{}".format(
                os.path.join(co, "lib"), os.path.join(lgp, "lib"), os.path.join(las, "lib")
            ),
        )
        pkg_config = self._find_pkg_config_tool()
        if pkg_config:
            env.define("PKG_CONFIG", pkg_config)
        env.define("GPGRT_CONFIG", os.path.join(co, "bin", "gpgrt-config"))
        env.define("GPG_ERROR_CONFIG", os.path.join(co, "bin", "gpgrt-config"))
        env.define("LIBASSUAN_CONFIG", os.path.join(co, "bin", "libassuan-config"))
        env.prepend_path("PKG_CONFIG_PATH", os.path.join(co, "lib", "pkgconfig"))
        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            moc = os.path.join(qtbase.package_folder, "libexec", "moc")
            if os.path.isfile(moc) and os.access(moc, os.X_OK):
                env.define("MOC6", moc)
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                env.prepend_path(
                    "PKG_CONFIG_PATH",
                    os.path.join(dep.package_folder, "lib", "pkgconfig"),
                )
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "libexec"))
        env.prepend_path("PATH", os.path.join(co, "bin"))
        env.prepend_path("PKG_CONFIG_PATH", os.path.join(co, "lib", "pkgconfig"))
        return env

    @staticmethod
    def _build_shell():
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("bash"),
            shutil.which("sh"),
            "/system/bin/sh",
            "/bin/sh",
        ):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return os.path.abspath(candidate)
        return "sh"

    @staticmethod
    def _find_tool_near_compiler(compilers, names):
        search_dirs = []
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                directory = os.path.dirname(compiler)
                if directory not in search_dirs:
                    search_dirs.append(directory)
        for name in names:
            for directory in search_dirs:
                candidate = os.path.join(directory, name)
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return os.path.abspath(candidate)
            found = shutil.which(name)
            if found:
                return os.path.abspath(found)
        return None

    def _find_pkg_config_tool(self):
        for dep in self.dependencies.build.values():
            if dep and dep.package_folder:
                for name in ("pkgconf", "pkg-config"):
                    candidate = os.path.join(dep.package_folder, "bin", name)
                    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                        return os.path.abspath(candidate)
        for name in ("pkgconf", "pkg-config"):
            found = shutil.which(name)
            if found:
                return os.path.abspath(found)
        return None

    # ------------------------------------------------------------------ #
    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        AutotoolsDeps(self).generate()

    def _configure_args(self):
        args = [
            "./configure",
            "--prefix=/",
            "--libdir=/lib",
            "--includedir=/include",
            "--disable-nls",
            "--disable-doc",
            "--disable-werror",
            "--enable-languages=cpp,qt6",
        ]
        if self.options.shared:
            args += ["--enable-shared", "--disable-static"]
        else:
            args += ["--disable-shared", "--enable-static"]
        args.append(
            "--with-libgpg-error-prefix={}".format(
                shlex.quote(self.dependencies["libgpg-error"].package_folder)
            )
        )
        return args

    def build(self):
        apply_conandata_patches(self)
        co = self._create_config_overrides()
        env = self._build_env(co)
        with env.vars(self).apply():
            self.run(" ".join(self._configure_args()), env=None, cwd=self.source_folder)
            # Most tests require a GnuPG runtime, but these two C API tests only
            # exercise GPGME version and data abstractions. Keep them enabled so
            # the package proves its runtime-independent core on OHOS.
            for subdir in ("src", "lang/cpp/src", "lang/qt/src"):
                self.run(f"make -C {subdir} -j1", env=None, cwd=self.source_folder)
            for test in ("t-version", "t-data", "t-engine-info"):
                self.run(f"make -C tests {test} -j1", env=None, cwd=self.source_folder)
                self.run(f"./{test}", env=None, cwd=os.path.join(self.source_folder, "tests"))

    def package(self):
        co = self._co_dir()
        env = self._build_env(co)
        with env.vars(self).apply():
            for subdir in ("src", "lang/cpp/src", "lang/qt/src"):
                self.run(
                    "make -C {} install DESTDIR={} -j1".format(
                        subdir, shlex.quote(self.package_folder)
                    ),
                    env=None,
                    cwd=self.source_folder,
                )
        # Remove build-machine-specific libtool .la files.
        import glob

        for la in glob.glob(os.path.join(self.package_folder, "**", "*.la"), recursive=True):
            os.unlink(la)
        self._write_relocatable_cmake_configs()

    def _write_relocatable_cmake_configs(self):
        cmake_root = os.path.join(self.package_folder, "lib", "cmake")
        os.makedirs(os.path.join(cmake_root, "gpgme"), exist_ok=True)
        os.makedirs(os.path.join(cmake_root, "Gpgmepp"), exist_ok=True)
        os.makedirs(os.path.join(cmake_root, "QGpgmeQt6"), exist_ok=True)
        gpgme_config = os.path.join(cmake_root, "gpgme", "gpgmeConfig.cmake")
        with open(gpgme_config, "w", encoding="utf-8") as f:
            f.write(
                """include(CMakeFindDependencyMacro)

find_dependency(libassuan CONFIG QUIET)
find_dependency(libgpg-error CONFIG QUIET)

get_filename_component(_GPGME_PREFIX "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)

if(NOT TARGET gpgme::gpgme)
  add_library(gpgme::gpgme SHARED IMPORTED)
  set_target_properties(gpgme::gpgme PROPERTIES
    IMPORTED_LOCATION "${_GPGME_PREFIX}/lib/libgpgme.so"
    INTERFACE_INCLUDE_DIRECTORIES "${_GPGME_PREFIX}/include"
  )
  if(TARGET libassuan::libassuan)
    set_property(TARGET gpgme::gpgme APPEND PROPERTY INTERFACE_LINK_LIBRARIES libassuan::libassuan)
  endif()
  if(TARGET libgpg-error::libgpg-error)
    set_property(TARGET gpgme::gpgme APPEND PROPERTY INTERFACE_LINK_LIBRARIES libgpg-error::libgpg-error)
  endif()
endif()
"""
            )

        gpgmepp_config = os.path.join(cmake_root, "Gpgmepp", "GpgmeppConfig.cmake")
        with open(gpgmepp_config, "w", encoding="utf-8") as f:
            f.write(
                """include(CMakeFindDependencyMacro)

find_dependency(gpgme CONFIG REQUIRED)

get_filename_component(_GPGME_PREFIX "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)

if(NOT TARGET Gpgmepp)
  add_library(Gpgmepp SHARED IMPORTED)
  set_target_properties(Gpgmepp PROPERTIES
    IMPORTED_LOCATION "${_GPGME_PREFIX}/lib/libgpgmepp.so"
    INTERFACE_INCLUDE_DIRECTORIES "${_GPGME_PREFIX}/include/gpgme++;${_GPGME_PREFIX}/include"
    INTERFACE_LINK_LIBRARIES "gpgme::gpgme"
  )
endif()
"""
            )

        qgpgme_config = os.path.join(cmake_root, "QGpgmeQt6", "QGpgmeQt6Config.cmake")
        with open(qgpgme_config, "w", encoding="utf-8") as f:
            f.write(
                """include(CMakeFindDependencyMacro)

find_dependency(Qt6 CONFIG REQUIRED COMPONENTS Core)
find_dependency(Gpgmepp CONFIG REQUIRED)

get_filename_component(_GPGME_PREFIX "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)

if(NOT TARGET QGpgmeQt6)
  add_library(QGpgmeQt6 SHARED IMPORTED)
  set_target_properties(QGpgmeQt6 PROPERTIES
    IMPORTED_LOCATION "${_GPGME_PREFIX}/lib/libqgpgmeqt6.so"
    INTERFACE_INCLUDE_DIRECTORIES "${_GPGME_PREFIX}/include/qgpgme-qt6/qgpgme;${_GPGME_PREFIX}/include/qgpgme-qt6"
    INTERFACE_LINK_LIBRARIES "Gpgmepp;Qt6::Core"
  )
endif()
"""
            )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gpgme")
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]

        core = self.cpp_info.components["gpgme"]
        core.libs = ["gpgme"]
        core.requires = [
            "libgpg-error::libgpg-error",
            "libassuan::libassuan",
        ]
        core.set_property("pkg_config_name", "gpgme")
        core.set_property("cmake_target_name", "gpgme::gpgme")
        if self.settings.os in ("Linux", "OHOS"):
            core.system_libs = ["pthread"]

        cpp = self.cpp_info.components["gpgmepp"]
        cpp.libs = ["gpgmepp"]
        cpp.requires = ["gpgme"]
        cpp.set_property("pkg_config_name", "gpgmepp")
        cpp.set_property("cmake_target_name", "Gpgmepp")

        qt6 = self.cpp_info.components["qgpgmeqt6"]
        qt6.libs = ["qgpgmeqt6"]
        qt6.requires = ["gpgmepp", "qtbase::core"]
        qt6.set_property("pkg_config_name", "qgpgmeqt6")
        qt6.set_property("cmake_target_name", "QGpgmeQt6")
