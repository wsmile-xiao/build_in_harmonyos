import os
import shutil
from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.microsoft import unix_path


class TestPkg(ConanFile):
    """R34 test package for guile 2.2.7 - compiles and links against libguile-2.2."""

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        include_dirs = []
        lib_dirs = []
        for dep in self.dependencies.host.values():
            include_dirs.extend(dep.cpp_info.includedirs)
            lib_dirs.extend(dep.cpp_info.libdirs)
        guile = self.dependencies["guile"].cpp_info
        inc_flags = " ".join("-I" + unix_path(self, d) for d in include_dirs)
        libdir = guile.libdirs[0] if guile.libdirs else os.path.join(
            guile.rootpath, "lib"
        )
        lib_flags = " ".join("-L" + unix_path(self, d) for d in lib_dirs)
        cc = os.environ.get("CC") or self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")
        if self.settings.os == "OHOS" and not os.path.exists(cc):
            resolved = shutil.which("clang")
            if resolved:
                cc = "sh {}".format(unix_path(self, resolved))
        # R34: Compile + link against libguile-2.2 to verify the package.
        # -Wl,--allow-shlib-undefined tolerates transitive deps (libgc, libgmp, etc.)
        #   that are not in the immediate link search path.
        self.run(
            f"{cc} test.c -o test_probe "
            f"{inc_flags} -L{unix_path(self, libdir)} {lib_flags} -lguile-2.2 "
            f"-Wl,--allow-shlib-undefined"
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: R34 compile+link check only")
            return
        # Runtime failures must fail conan create: a link-only pass cannot
        # establish that downstream applications can use libguile.
        self.run("guile --version", env="conanrun")
        self.run("guile -c '(exit (if (= (+ 1 2) 3) 0 1))'", env="conanrun")
        self.run("guild --version", env="conanrun")
        self.run("guile-config --version", env="conanrun")
        self.run("guile-config compile", env="conanrun")
        self.run("guile-config link", env="conanrun")
        self.run("./test_probe", env="conanrun")
