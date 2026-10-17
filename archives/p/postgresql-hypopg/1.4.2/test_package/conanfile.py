import os

from conan import ConanFile


class PostgresqlHypopgTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        libdir = self.dependencies["postgresql-hypopg"].cpp_info.libdirs[0]
        so_path = os.path.join(libdir, "hypopg.so")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} {os.path.join(self.source_folder, 'test.sh')} {so_path}", env="conanrun")
