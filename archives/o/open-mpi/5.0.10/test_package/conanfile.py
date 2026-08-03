import os
from conan import ConanFile


class OpenMpiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dependency = self.dependencies["open-mpi"]
        include_flags = " ".join(f'-I"{path}"' for path in dependency.cpp_info.includedirs)
        library_flags = " ".join(f'-L"{path}"' for path in dependency.cpp_info.libdirs)
        libraries = " ".join(f"-l{library}" for library in dependency.cpp_info.libs)
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "cc")
        self.run(f'{cc} test_mpi.c -o test_mpi {include_flags} {library_flags} {libraries}')

    def test(self):
        package = self.dependencies["open-mpi"].package_folder
        mpirun = os.path.join(package, "bin", "mpirun")
        mpi_header = os.path.join(package, "include", "mpi.h")
        assert os.path.isfile(mpirun), "mpirun was not packaged"
        assert os.path.isfile(mpi_header), "mpi.h was not packaged"
        # The OHOS sandbox blocks the process-management syscalls used by
        # mpirun. Open MPI singleton mode still initializes the installed
        # MPI library without launching a second rank.
        self.run("bash -c './test_mpi'", env="conanrun")
