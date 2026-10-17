#!/usr/bin/env python3
"""Conan recipe — latino 1.4.4 (CMake, CLI interpreter + library).

Latino is a programming language with Spanish-syntax keywords built on a
bytecode VM (latino-core). The upstream superproject builds:
  - bin/latino      : the interpreter executable
  - lib/liblatino.so: shared library (target liblatino, OUTPUT_NAME latino)
  - lib/liblatino_static.a
  - 14 public headers, man page, desktop/nanorc data files

Upstream CMake peculiarities handled here:
  * The GitHub v1.4.4 tarball omits the latino-core submodule; it is fetched
    from the commit pinned by the superproject and restored in place.
  * Upstream calls bare `link_libraries(readline)` (no find_package), so the
    Conan readline package is injected via CPATH/LIBRARY_PATH.
  * `if(UNIX)` guards every install(TARGETS)/install(FILES) rule; CMake has
    no HarmonyOS platform module (E092), so CMAKE_SYSTEM_NAME is mapped to
    Linux, matching the OHOS musl/libc environment (clang defines __linux__).
  * Upstream always builds both shared and static libraries; the `shared`
    option only selects which one is packaged.
  * GetLatVersion.cmake rewrites latino-core/include/latino.h in the source
    folder (LAT_CURRENT_YEAR stamp); the conan source folder is writable.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get, rm, save)


class LatinoConan(ConanFile):
    name = "latino"
    version = "1.4.4"
    description = "Lenguaje de programación de código abierto con sintaxis en español (interpreter + embeddable library)."
    license = "MIT"
    homepage = "https://lenguaje-latino.github.io/"
    url = "https://github.com/lenguaje-latino/latino"
    topics = ("interpreter", "language", "spanish", "vm")
    package_type = "library"
    languages = "C"
    implements = ["auto_shared_fpic"]

    # Binary stays self-contained: readline is linked statically from Conan
    # (see requirements), so the interpreter runs without extra runpath.
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # Upstream: link_libraries(readline) in latino-core/src/CMakeLists.txt.
        # Default static so both the executable and liblatino.so stay
        # self-contained on OHOS (no system libreadline.so).
        # transitive_headers: the public latcompat.h includes
        # <readline/readline.h>/<readline/history.h> in the __linux__ branch
        # (OHOS clang defines __linux__), so consumers compiling against
        # latino's headers must see readline's include dirs. Without this
        # trait a shared latino would propagate headers=False and CMakeDeps
        # would skip generating readline's config for consumers.
        self.requires("readline/8.3", transitive_headers=True)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # Main tarball (superproject)
        get(self, **self.conan_data["sources"][0], strip_root=True)
        # Restore the latino-core submodule pinned by the superproject:
        # the root CMakeLists expects <src>/latino-core/.
        get(self, **self.conan_data["sources"][1],
            destination="latino-core", strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake has no HarmonyOS platform module; with the OHOS
        # CMakeToolchain default (CMAKE_SYSTEM_NAME=HarmonyOS) UNIX evaluates
        # false and every upstream install() rule (guarded by if(UNIX)) is
        # skipped, leaving an empty package. HarmonyOS/musl is Linux-kernel
        # compatible for this pure C project and the OHOS clang defines
        # __linux__, so the Linux branch applies verbatim.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Upstream defaults to Debug when CMAKE_BUILD_TYPE is unset.
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # Release flags: use conan flags + upstream Release baseline.
        tc.variables["CMAKE_C_FLAGS_RELEASE"] = "-O3 -DNDEBUG"
        # Upstream links a bare `-lreadline` (no find_package) and never
        # links ncurses, but readline's terminfo symbols (tputs/UP/tgetflag)
        # live in ncursesw. CMAKE_C_STANDARD_LIBRARIES is appended by CMake
        # to the END of every link line (after -lreadline), which keeps the
        # static-archive symbol order valid.
        ncurses = self.dependencies["ncurses"]
        tc.variables["CMAKE_C_STANDARD_LIBRARIES"] = " ".join(
            f"-l{lib}" for lib in ncurses.cpp_info.libs)
        # Install rules use ${CMAKE_INSTALL_PREFIX}/bin etc. (CMAKE_INSTALL_
        # PREFIX is set by CMakeToolchain automatically).
        tc.generate()

        # Upstream uses bare `link_libraries(readline)` / `#include
        # <readline/readline.h>` without any find_package; inject the Conan
        # readline package through compiler/linker search paths (CPATH and
        # LIBRARY_PATH are honored by clang for -I and -L resolution).
        env = Environment()
        readline = self.dependencies["readline"]
        cpaths = []
        libpaths = []
        for includedir in readline.cpp_info.includedirs:
            cpaths.append(includedir)
        for libdir in readline.cpp_info.libdirs:
            libpaths.append(libdir)
        # ncurses is a transitive dependency of readline; its headers are not
        # needed (readline installs its own readline/*.h), but its libraries
        # must be findable at link time when readline is shared.
        ncurses = self.dependencies["ncurses"]
        for libdir in ncurses.cpp_info.libdirs:
            libpaths.append(libdir)
        # CPATH/LIBRARY_PATH are ':'-separated lists; write once via define
        # (append/prepend would join with spaces and break the list).
        if cpaths:
            env.define("CPATH", ":".join(cpaths))
        if libpaths:
            env.define("LIBRARY_PATH", ":".join(libpaths))
        env.vars(self, scope="build").save_script("conanbuild_readline")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Upstream official test: ctest -R coverage
        # (add_test(NAME coverage COMMAND latino ejemplos/coverage.lat)).
        # ejemplos/ sits in the superproject source dir; the binary dir has
        # none of it, so run the interpreter directly against the source path.
        self.run(
            f'"{self.build_folder}/latino" '
            f'"{self.source_folder}/ejemplos/coverage.lat"',
            env="conanbuild")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Drop the artifact not selected by the `shared` option (upstream
        # builds both). Upstream's static target is named liblatino_static,
        # which CMake installs as libliblatino_static.a; rename it to
        # liblatino.a so -llatino resolves in both modes. The interpreter
        # binary is kept in all cases.
        if self.options.shared:
            rm(self, "libliblatino_static.a", os.path.join(self.package_folder, "lib"))
        else:
            libdir = os.path.join(self.package_folder, "lib")
            static_lib = os.path.join(libdir, "libliblatino_static.a")
            # Upstream defect (all platforms, not OHOS-specific): the static
            # library is built from SRC_LIB which includes latino.c — the
            # file that defines main(). Any consumer with its own main()
            # fails to link with a duplicate-symbol error. latino.o also
            # defines the two public globals `filename` and `parse_silent`
            # referenced by latast.c/latlex.c/latparse.c, so we replace the
            # object with a stub providing exactly those globals (main is
            # intentionally dropped: the CLI binary ships it).
            # Replace latino.o (which defines main()) with a stub providing
            # exactly the two public globals it also defines; compile the
            # stub with the build environment (CC/AR from the profile).
            # tools.build:compiler_executables from the profile (also what
            # CMakeToolchain feeds into CMAKE_C_COMPILER); ar lives next to
            # the compiler as llvm-ar.
            cc = self.conf.get("tools.build:compiler_executables")["c"]
            ar = os.path.join(os.path.dirname(cc), "llvm-ar")
            self.run(f'"{ar}" d "{static_lib}" latino.o')
            stub = os.path.join(self.build_folder, "latino_globals_stub.c")
            stub_o = os.path.join(self.build_folder, "latino_globals_stub.o")
            save(self, stub,
                 "/* Public globals defined in latino.c (which also defines\n"
                 " * main(), excluded from the static library). */\n"
                 "#include <stddef.h>\n"
                 "char *filename = NULL;\n"
                 "int parse_silent = 0;\n")
            self.run(f'"{cc}" -c "{stub}" -o "{stub_o}"')
            self.run(f'"{ar}" r "{static_lib}" "{stub_o}"')
            dst = os.path.join(libdir, "liblatino.a")
            os.rename(static_lib, dst)
            rm(self, "liblatino.so", libdir)

    def package_info(self):
        # Explicit component so CMakeDeps propagates readline's include dirs
        # and libs transitively: the public latcompat.h header includes
        # <readline/history.h> in the __linux__ branch (OHOS clang defines
        # __linux__), so consumers must see readline's headers through
        # target_link_libraries(latino::latino).
        self.cpp_info.set_property("cmake_file_name", "latino")
        self.cpp_info.components["latino"].set_property(
            "cmake_target_name", "latino::latino")
        self.cpp_info.components["latino"].libs = ["latino"]
        self.cpp_info.components["latino"].requires = ["readline::readline"]
