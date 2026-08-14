#!/usr/bin/env python3
"""Conan 2 recipe for acepack 1.6.3 on native HarmonyOS aarch64.

acepack is an R package (ACE and AVAS for Selecting Multiple Regression
Transformations) that ships 17 Fortran 90 sources plus one C file. It is
installed into an R library tree via ``R CMD INSTALL`` using the
``r-base/4.5.1`` Conan package as host runtime.

Key points:
- ``requires("r-base/4.5.1")`` provides R_HOME (lib/R), bin/R, bin/Rscript.
- ``tool_requires("flang-ohos/20.1.0")`` provides the Fortran compiler.
- The packaged r-base Makeconf has ``FC = false`` (relocatable cleanup) and
  R CMD SHLIB processes ``-f Makevars`` BEFORE ``-f Makeconf``, so a plain
  src/Makevars FC override is shadowed. This recipe therefore writes a site
  Makevars file and points ``R_MAKEVARS_SITE`` at it (included after
  Makeconf), so the injected flang FC/F77/FLIBS toolchain takes effect.
- ``build()`` runs ``R CMD INSTALL --library <staging>``.
- ``package()`` lays out ``lib/R/library/acepack/``.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class AcepackConan(ConanFile):
    name = "acepack"
    version = "1.6.3"
    description = "ACE and AVAS for Selecting Multiple Regression Transformations"
    license = "MIT"
    homepage = "https://cran.r-project.org/package=acepack"
    url = "https://cran.r-project.org/src/contrib/acepack_1.6.3.tar.gz"
    topics = ("r", "r-package", "regression", "ace", "avas", "ohos")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    options = {"shared": [True, False]}
    default_options = {"shared": False}


    def requirements(self):
        self.requires("r-base/4.5.1")

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def source(self):
        get(
            self,
            **self.conan_data["sources"]["acepack"],
            destination=self.source_folder,
            strip_root=True,
        )

    def _get_conf_tool(self, key, default, check_type=str):
        """Fetch a compiler executable path from Conan conf.

        Falls back to default if conf is not set.
        """
        try:
            return self.conf.get(key, default, check_type=check_type)
        except Exception:
            return default

    def _r_home(self):
        rbase = self.dependencies.host["r-base"]
        return os.path.join(rbase.package_folder, "lib", "R")

    def _r_bin(self):
        rbase = self.dependencies.host["r-base"]
        return os.path.join(rbase.package_folder, "bin", "R")

    def _rscript_bin(self):
        rbase = self.dependencies.host["r-base"]
        return os.path.join(rbase.package_folder, "bin", "Rscript")

    def _flang(self):
        flang = self.dependencies.build["flang-ohos"]
        folder = flang.package_folder
        return folder, os.path.join(folder, "bin", "flang")

    def build(self):
        r_home = self._r_home()
        r_bin = self._r_bin()
        flang_folder, flang = self._flang()

        if not os.path.isfile(r_bin):
            raise ConanException(f"R launcher not found: {r_bin}")

        staging_lib = os.path.join(self.build_folder, "r-libs")
        os.makedirs(staging_lib, mode=0o755)

        # 注入 Fortran 编译链：r-base 制品 Makeconf 中 FC=false（打包时清理），
        # R CMD SHLIB 的 make 顺序为 -f Makevars -f Makeconf -f shlib.mk，
        # Makeconf 后于 Makevars 处理，故 Makevars 中的 FC 赋值被 Makeconf 覆盖。
        # 解法：用 R_MAKEVARS_SITE 环境变量指定 site Makevars 文件，
        # 该文件在 Makeconf 之后被 include，从而正确覆盖 FC=false。
        flang_libdir = os.path.join(flang_folder, "lib")
        site_makevars = os.path.join(self.build_folder, "flang-makevars.mk")
        with open(site_makevars, "w", encoding="utf-8") as stream:
            stream.write("## OHOS flang toolchain injection (acepack recipe)\n")
            stream.write(f"FC = {flang}\n")
            stream.write(f"F77 = {flang}\n")
            stream.write("FCFLAGS = -g -O2 -fPIC\n")
            stream.write("FFLAGS = -g -O2 -fPIC\n")
            stream.write(
                "FLIBS = -L{libdir} -lFortranRuntime -lFortranDecimal "
                "-lFortranCommon -lm\n".format(libdir=flang_libdir)
            )

        rbase = self.dependencies.host["r-base"]
        env = os.environ.copy()
        env["R_HOME"] = r_home
        env["R_LIBS_USER"] = staging_lib
        env["PATH"] = os.pathsep.join([
            os.path.join(rbase.package_folder, "bin"),
            "/data/service/hnp/bin",
            "/system/bin",
            "/bin",
            "/usr/bin",
            env.get("PATH", ""),
        ])
        env["TMPDIR"] = env.get("TMPDIR", os.path.join(os.path.expanduser("~"), "tmp"))
        env["TMP"] = env["TMPDIR"]
        env["TEMP"] = env["TMPDIR"]
        cc = self._get_conf_tool("tools.build:compiler_executables:c", "clang")
        cxx = self._get_conf_tool("tools.build:compiler_executables:cpp", "clang++")
        ar = self._get_conf_tool("tools.build:compiler_executables:ar", "llvm-ar")
        ranlib = self._get_conf_tool("tools.build:compiler_executables:ranlib", "llvm-ranlib")
        env["CC"] = cc
        env["CXX"] = cxx
        env["AR"] = ar
        env["RANLIB"] = ranlib
        env["R_MAKEVARS_SITE"] = site_makevars
        env["R_LD_LIBRARY_PATH"] = os.path.join(r_home, "lib")
        env["LD_LIBRARY_PATH"] = os.pathsep.join([
            os.path.join(flang_folder, "lib"),
            os.path.join(r_home, "lib"),
            env.get("LD_LIBRARY_PATH", ""),
        ])

        cmd = [r_bin, "CMD", "INSTALL", "--library", staging_lib, self.source_folder]
        self.output.info("Running: " + " ".join(cmd))
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
        self.output.info(result.stdout)
        if result.returncode:
            self.output.info(result.stderr)
            raise ConanException(
                f"R CMD INSTALL failed with exit code {result.returncode}"
            )

        installed_pkg = os.path.join(staging_lib, "acepack")
        if not os.path.isdir(installed_pkg):
            raise ConanException(
                f"acepack R package was not installed to {installed_pkg}"
            )
        self.output.info("ACEPACK_R_CMD_INSTALL=PASS")

    def package(self):
        staging_lib = os.path.join(self.build_folder, "r-libs")
        if not os.path.isdir(staging_lib):
            raise ConanException("R library staging directory is missing")
        installed_pkg = os.path.join(staging_lib, "acepack")
        if not os.path.isdir(installed_pkg):
            raise ConanException("acepack R package installation not found")

        dest_r_lib = os.path.join(self.package_folder, "lib", "R", "library")
        os.makedirs(dest_r_lib, mode=0o755)
        shutil.copytree(
            installed_pkg,
            os.path.join(dest_r_lib, "acepack"),
            symlinks=False,
        )

        license_file = os.path.join(self.source_folder, "LICENSE")
        if os.path.isfile(license_file):
            licenses_dir = os.path.join(self.package_folder, "licenses")
            os.makedirs(licenses_dir, mode=0o755)
            shutil.copy2(
                license_file,
                os.path.join(licenses_dir, "LICENSE"),
            )

    def package_info(self):
        r_lib_dir = os.path.join(self.package_folder, "lib", "R", "library")
        # acepack is an R library package, no bin/ executables
        self.runenv_info.define_path("R_ACEPACK_LIB", r_lib_dir)
        self.buildenv_info.define_path("R_ACEPACK_LIB", r_lib_dir)
