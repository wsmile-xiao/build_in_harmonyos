"""Real MPI / Flang ABI MUMPS repair, retaining all eleven upstream examples."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from shlex import quote

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save


class MumpsConan(ConanFile):
    name = "mumps"
    version = "5.9.1.1"
    description = "Parallel MUMPS sparse solver with real MPI and writable save/restore fixtures"
    license = "CeCILL-C"
    homepage = "https://mumps-solver.org/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True], "parallel": [True]}
    default_options = {"shared": True, "parallel": True}
    exports_sources = "native_driver.py", "run_original_examples.py"

    def requirements(self):
        self.requires("mpich/5.0.1.2", transitive_headers=True, transitive_libs=True)
        self.requires("scalapack/2.2.3", transitive_libs=True)
        self.requires("openblas/0.3.34", transitive_libs=True)

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0", package_id_mode="full_mode")

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("This parallel ABI is validated for OHOS/armv8 only")
        if self.settings_build.os != self.settings.os or self.settings_build.arch != self.settings.arch:
            raise ConanInvalidConfiguration("MUMPS upstream MPI tests require native build=host")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _inputs(self):
        configured = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = configured.get("c") or shutil.which("clang")
        if not cc:
            raise ConanInvalidConfiguration("No configured native C compiler")
        resource = Path(subprocess.check_output([cc, "-print-resource-dir"], text=True).strip()).resolve()
        llvm = resource.parent.parent.parent
        # SDK installations may co-locate sysroot with bin/lib, or put them
        # under native/llvm and native/sysroot. Do not assume the latter layout.
        native = llvm if (llvm / "sysroot/usr/lib/aarch64-linux-ohos/Scrt1.o").is_file() else llvm.parent
        raw = llvm / "bin/clang-15"
        if not raw.is_file():
            raw = llvm / "bin/clang"
        flang = Path(self.dependencies.build["flang-ohos"].package_folder)
        mpi = Path(self.dependencies["mpich"].package_folder)
        blas = Path(self.dependencies["openblas"].package_folder)
        scalapack = Path(self.dependencies["scalapack"].package_folder)
        paths = {"raw_cc": str(raw), "resource": str(resource), "sysroot": str(native / "sysroot"),
                 "llvm_bin": str(llvm / "bin"), "llvm_lib": str(llvm / "lib"),
                 "target_lib": str(llvm / "lib/aarch64-linux-ohos"), "flang": str(flang),
                 "mpi": str(mpi), "blas": str(blas), "scalapack": str(scalapack),
                 "signer": shutil.which("binary-sign-tool"), "readelf": shutil.which("llvm-readelf"),
                 "objcopy": shutil.which("llvm-objcopy")}
        required = [raw, resource, native / "sysroot/usr/lib/aarch64-linux-ohos/Scrt1.o",
                    flang / "bin/flang", mpi / "bin/mpifort", mpi / "bin/mpiexec",
                    mpi / "include/mpi.h", mpi / "include/mpif.h", mpi / "lib/libmpifort.so",
                    blas / "lib/libopenblas.so", scalapack / "lib/libscalapack.so"]
        required.extend(flang / "lib" / x for x in ("libFortranRuntime.a", "libFortranDecimal.a", "libFortranCommon.a"))
        missing = [str(p) for p in required if not p.exists()]
        missing.extend("tool:" + x for x in ("signer", "readelf", "objcopy") if not paths[x])
        if missing:
            raise ConanInvalidConfiguration("Incomplete native Fortran MPI/compiler/signing closure: " + ", ".join(missing))
        paths["build_root"] = self.source_folder
        return paths

    def build(self):
        apply_conandata_patches(self)
        inputs = self._inputs()
        save(self, os.path.join(self.source_folder, "native-inputs.json"), json.dumps(inputs))
        driver = quote(sys.executable) + " " + quote(os.path.join(self.source_folder, "native_driver.py"))
        make = shutil.which("make")
        ar = shutil.which("llvm-ar")
        ranlib = shutil.which("llvm-ranlib")
        if not all((make, ar, ranlib)):
            raise ConanInvalidConfiguration("Native make/archive tools are missing")
        lines = ["PLAT =", "LIBEXT_SHARED = .so", "SONAME = -soname", "SHARED_OPT = -shared",
                 "FPIC_OPT = -fPIC", "LIBEXT = .a", "OUTC = -o ", "OUTF = -o ", "RM = rm -f",
                 "CC = " + driver + " c", "FC = " + driver + " fortran", "FL = " + driver + " fortran",
                 "AR = " + quote(ar) + " vr", "RANLIB = " + quote(ranlib),
                 "LPORDDIR = $(topdir)/PORD/lib", "IPORD = -I$(topdir)/PORD/include",
                 "LPORD = -L$(LPORDDIR) -lpord", "ORDERINGSF = -Dpord", "ORDERINGSC = $(ORDERINGSF)",
                 "LORDERINGS = $(LPORD)", "IORDERINGSF =", "IORDERINGSC = $(IPORD)",
                 "LAPACK = " + inputs["blas"] + "/lib/libopenblas.so",
                 "SCALAP = " + inputs["scalapack"] + "/lib/libscalapack.so",
                 "INCPAR = -I" + inputs["mpi"] + "/include", "LIBPAR = $(SCALAP) $(LAPACK)",
                 "LIBBLAS = $(LAPACK)", "LIBOTHERS = -lpthread -lm", "CDEFS = -DAdd_",
                 "OPTF = -O2 -fPIC", "OPTC = -O2 -fPIC", "OPTL = -O2",
                 "INCS = $(INCPAR)", "LIBS = $(LIBPAR)", "LIBSEQNEEDED =",
                 "RPATH_OPT = -Wl,-rpath," + self.source_folder + "/lib"]
        save(self, os.path.join(self.source_folder, "Makefile.inc"), "\n".join(lines) + "\n")
        environment = os.environ.copy()
        environment["LD_LIBRARY_PATH"] = os.pathsep.join([inputs["llvm_lib"], inputs["flang"] + "/lib",
            self.source_folder + "/lib", inputs["mpi"] + "/lib", inputs["blas"] + "/lib", inputs["scalapack"] + "/lib"])
        environment.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", HYDRA_LAUNCHER="fork", HYDRA_BINDING="none")
        subprocess.run([make, "-j1", "allshared"], cwd=self.source_folder, env=environment, check=True, timeout=3600)
        self.run(quote(sys.executable) + " " + quote(os.path.join(self.source_folder, "run_original_examples.py")),
                 cwd=self.source_folder, env="conanrun")

    def package(self):
        copy(self, "*.so*", src=os.path.join(self.source_folder, "lib"), dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"), dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "*.mod", src=os.path.join(self.source_folder, "src"), dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "CeCILL-C_V1-*.txt", src=os.path.join(self.source_folder, "doc"), dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        for library in ("smumps", "dmumps", "cmumps", "zmumps", "mumps_common", "pord"):
            name = "lib" + library + ".so"
            path = os.path.join(self.package_folder, "lib", name)
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration("Missing actual packaged arithmetic library: " + library)
            readelf = shutil.which("llvm-readelf")
            if not readelf:
                raise ConanInvalidConfiguration("Cannot verify the delivered ELF dynamic identity")
            dynamic = subprocess.check_output([readelf, "-d", path], text=True)
            sonames = re.findall(r"\(SONAME\).*?\[([^\]]+)\]", dynamic)
            needed = re.findall(r"\(NEEDED\).*?\[([^\]]+)\]", dynamic)
            if sonames != [name] or any("/" in dependency for dependency in needed):
                raise ConanInvalidConfiguration("Invalid SONAME or path-dependent NEEDED: " + name)
            self.output.info("DELIVERED_ELF_IDENTITY=" + name + " SONAME=" + sonames[0])
        self.output.info("MUMPS_SONAME_PASS=6/6")
        # Never install libseq/mpi.h: this package exposes the real published MPI ABI.

    def package_info(self):
        self.cpp_info.libs = ["dmumps", "smumps", "zmumps", "cmumps", "mumps_common", "pord"]
        self.cpp_info.requires = ["mpich::fortran", "scalapack::scalapack", "openblas::openblas"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("cmake_file_name", "mumps")
        self.cpp_info.set_property("cmake_target_name", "mumps::mumps")
        self.cpp_info.set_property("pkg_config_name", "mumps")
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
