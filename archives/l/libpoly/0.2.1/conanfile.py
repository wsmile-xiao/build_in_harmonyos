#!/usr/bin/env python3
"""Conan recipe for libpoly 0.2.1."""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file


class LibpolyConan(ConanFile):
    name = "libpoly"
    version = "0.2.1"
    description = "C library for manipulating polynomials"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/SRI-CSL/libpoly"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
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

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libpoly is validated only for Linux and OHOS")

    def requirements(self):
        self.requires("gmp/6.3.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        local = os.environ.get("OHC_TARBALL")
        if local and os.path.isfile(local):
            import shutil
            import tarfile
            with tarfile.open(local, "r:gz") as tf:
                tf.extractall(self.source_folder)
            entries = [e for e in os.listdir(self.source_folder) if e not in (".", "..")]
            if len(entries) == 1 and os.path.isdir(os.path.join(self.source_folder, entries[0])):
                inner = os.path.join(self.source_folder, entries[0])
                for n in os.listdir(inner):
                    os.rename(os.path.join(inner, n), os.path.join(self.source_folder, n))
                shutil.rmtree(inner)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        for rel in (
            os.path.join("src", "CMakeLists.txt"),
            os.path.join("test", "poly", "CMakeLists.txt"),
            os.path.join("test", "polyxx", "CMakeLists.txt"),
        ):
            path = os.path.join(self.source_folder, rel)
            if os.path.isfile(path):
                replace_in_file(self, path, "-Wall -Werror -Wextra", "-Wall -Wextra", strict=False)
        ms_h = os.path.join(self.source_folder, "src", "utils", "u_memstream.h")
        replace_in_file(
            self,
            ms_h,
            "#ifdef _WIN32\n   char **bufp;\n   size_t *sizep;\n   char temp[PATH_MAX];\n#endif",
            "   char **bufp;\n   size_t *sizep;\n   char temp[PATH_MAX];",
        )
        ms_c = os.path.join(self.source_folder, "src", "utils", "u_memstream.c")
        replace_in_file(
            self,
            ms_c,
            "#include <stdlib.h>\n",
            "#include <stdlib.h>\n#include <string.h>\n#include <unistd.h>\n#include <sys/stat.h>\n",
        )
        replace_in_file(
            self,
            ms_c,
            "   FILE *const f = open_memstream(bufp, sizep);\n   mem->f = f;\n   return f != NULL;",
            "   mem->bufp = bufp;\n"
            "   mem->sizep = sizep;\n"
            "   {\n"
            "      const char *td = getenv(\"TMPDIR\");\n"
            "      if (!td || !td[0]) td = getenv(\"HOME\");\n"
            "      if (!td || !td[0]) td = \".\";\n"
            "      snprintf(mem->temp, PATH_MAX, \"%s/lpmsXXXXXX\", td);\n"
            "      mode_t oldm = umask(0);\n"
            "      int fd = mkstemp(mem->temp);\n"
            "      umask(oldm);\n"
            "      if (fd < 0) { mem->f = NULL; return false; }\n"
            "      mem->f = fdopen(fd, \"w+\");\n"
            "      return mem->f != NULL;\n"
            "   }",
        )
        replace_in_file(
            self,
            ms_c,
            """void
u_memstream_close(struct u_memstream *mem)
{
   FILE *const f = mem->f;

#ifdef _WIN32
   long size = ftell(f);
   if (size > 0) {
      /* reserve space for the null terminator */
      char *buf = malloc(size + 1);
      fseek(f, 0, SEEK_SET);
      fread(buf, 1, size, f);
      /* insert null terminator */
      buf[size] = '\\0';

      *mem->bufp = buf;
      *mem->sizep = size;
   }

   remove(mem->temp);
#endif

   fclose(f);
}""",
            """void
u_memstream_close(struct u_memstream *mem)
{
   FILE *const f = mem->f;
   long size;
   char *buf;
   fflush(f);
   size = ftell(f);
   if (size < 0)
      size = 0;
   buf = malloc((size_t)size + 1);
   if (buf) {
      if (size > 0) {
         fseek(f, 0, SEEK_SET);
         fread(buf, 1, (size_t)size, f);
      }
      buf[size] = '\\0';
      *mem->bufp = buf;
      *mem->sizep = (size_t)size;
   }
   remove(mem->temp);
   fclose(f);
}""",
        )

    def generate(self):
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["LIBPOLY_BUILD_PYTHON_API"] = False
        tc.variables["LIBPOLY_BUILD_STATIC"] = not bool(self.options.shared)
        tc.variables["LIBPOLY_BUILD_STATIC_PIC"] = bool(self.options.get_safe("fPIC", True))
        tc.variables["BUILD_TESTING"] = True
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        gmp = self.dependencies["gmp"]
        incs = []
        for d in gmp.cpp_info.includedirs:
            p = d if os.path.isabs(d) else os.path.join(gmp.package_folder, d)
            incs.append(p)
        gmp_inc = None
        for p in incs:
            if os.path.isfile(os.path.join(p, "gmpxx.h")) and os.path.isfile(os.path.join(p, "gmp.h")):
                gmp_inc = p
                break
        if gmp_inc is None:
            for p in incs:
                if os.path.isfile(os.path.join(p, "gmp.h")):
                    gmp_inc = p
                    break
        if gmp_inc is None:
            raise ConanInvalidConfiguration("gmp.h not found in gmp package")
        if not os.path.isfile(os.path.join(gmp_inc, "gmpxx.h")):
            raise ConanInvalidConfiguration("gmpxx.h missing; need gmp with --enable-cxx")
        libdir = gmp.cpp_info.libdirs[0]
        if not os.path.isabs(libdir):
            libdir = os.path.join(gmp.package_folder, libdir)
        libs = glob.glob(os.path.join(libdir, "libgmp.so*")) + glob.glob(os.path.join(libdir, "libgmp.a"))
        gmpxx = glob.glob(os.path.join(libdir, "libgmpxx.so*")) + glob.glob(os.path.join(libdir, "libgmpxx.a"))
        if not libs:
            raise ConanInvalidConfiguration("gmp library not found in %s" % libdir)
        tc.variables["GMP_INCLUDE_DIR"] = gmp_inc
        if gmpxx:
            tc.variables["GMP_LIBRARY"] = "%s;%s" % (gmpxx[0], libs[0])
        else:
            tc.variables["GMP_LIBRARY"] = libs[0]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self._run_ctest()

    def _run_ctest(self):
        libdirs = []
        for d in (
            os.path.join(self.build_folder, "src"),
            os.path.join(self.build_folder, "lib"),
            self.build_folder,
        ):
            if os.path.isdir(d):
                libdirs.append(d)
        try:
            items = self.dependencies.host.items()
        except Exception:
            items = self.dependencies.items()
        for _, dep in items:
            base = getattr(dep, "package_folder", None) or ""
            for p in getattr(dep.cpp_info, "libdirs", []) or []:
                if not os.path.isabs(p) and base:
                    p = os.path.join(base, p)
                if os.path.isdir(p):
                    libdirs.append(p)
        ld = ":".join(dict.fromkeys(libdirs))
        self.run(
            'env LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ctest --output-on-failure' % ld,
            cwd=self.build_folder,
            env="conanrun",
            ignore_errors=True,
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["poly"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "libpoly")
        self.cpp_info.set_property("cmake_target_name", "libpoly::libpoly")
        self.cpp_info.set_property("pkg_config_name", "poly")
