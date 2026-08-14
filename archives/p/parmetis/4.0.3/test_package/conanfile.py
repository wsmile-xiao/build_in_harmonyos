import os
from conan import ConanFile


class ParmetisTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("open-mpi/5.0.10")

    def build(self):
        parmetis = self.dependencies["parmetis"]
        openmpi = self.dependencies["open-mpi"]
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "clang")
        mpi_root = openmpi.package_folder
        include_flags = " ".join(f'-I"{p}"' for p in parmetis.cpp_info.includedirs)
        lib_flags = " ".join(f'-L"{p}"' for p in parmetis.cpp_info.libdirs)
        libs = " ".join(f"-l{l}" for l in parmetis.cpp_info.libs)
        self.run(
            f'{cc} -I"{mpi_root}/include" test_parmetis.c -o test_parmetis '
            f'{include_flags} {lib_flags} {libs} -L"{mpi_root}/lib" -lmpi'
        )

    def test(self):
        # OHOS sandbox blocks mpirun process-management syscalls.
        # Run in MPI singleton mode (single rank, no mpirun needed),
        # same pattern as open-mpi test_package.
        # env="conanrun" activates open-mpi's runenv_info (OPAL_PREFIX, PATH).
        self.run("bash -c './test_parmetis'", env="conanrun")
