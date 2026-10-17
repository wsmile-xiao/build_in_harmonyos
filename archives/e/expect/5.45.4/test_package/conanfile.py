import os

from conan import ConanFile


class ExpectTestConan(ConanFile):
    """test_package for expect — runs test_expect.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Make tcl a direct test_package runtime requirement so that its
        # package_folder is resolved in the consumer test() lifecycle
        # (transitive dependency package_folder is None there).
        self.requires("tcl/8.6.14")

    def test(self):
        # Get the bin path from the dependency's package
        bin_dir = self.dependencies["expect"].cpp_info.bindirs[0]
        expect_bin = os.path.join(bin_dir, "expect")

        # Dynamically resolve the tcl package folder from the resolved dependency
        # graph (public consumer interface) and export TCL_LIBRARY at runtime so
        # Expect can locate tcl's lib/tcl8.6 (init.tcl etc.).
        tcl_pkg = self.dependencies["tcl"].package_folder
        tcl_library = os.path.join(tcl_pkg, "lib", "tcl8.6")

        # Verify expect binary exists
        self.run(f'test -x "{expect_bin}"', env="conanrun")

        # Run full smoke test suite via test_expect.sh
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'EXPECT_BIN="{expect_bin}" TCL_LIBRARY="{tcl_library}" {bash} test_expect.sh', env="conanrun")
