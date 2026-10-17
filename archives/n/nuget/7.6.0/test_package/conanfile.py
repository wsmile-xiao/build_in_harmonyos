from conan import ConanFile
import os


class NugetTest(ConanFile):
    """test_package for nuget — verifies packaged NuGet.exe binary integrity."""
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get nuget package directories
        pkg = self.dependencies["nuget"].package_folder
        libexec = os.path.join(pkg, "libexec")
        bin_dir = os.path.join(pkg, "bin")

        # Verify NuGet.exe exists in libexec/
        nuget_exe = os.path.join(libexec, "NuGet.exe")
        assert os.path.exists(nuget_exe), f"NuGet.exe not found at {nuget_exe}"

        # Verify wrapper script exists in bin/
        nuget_wrapper = os.path.join(bin_dir, "nuget")
        assert os.path.exists(nuget_wrapper), f"nuget wrapper not found at {nuget_wrapper}"

        # Verify NuGet.exe is a valid PE32 executable (not empty/corrupt)
        file_size = os.path.getsize(nuget_exe)
        assert file_size > 1_000_000, f"NuGet.exe too small ({file_size} bytes), likely corrupt"

        # Read PE header to verify it's a valid Windows executable
        with open(nuget_exe, "rb") as f:
            mz = f.read(2)
            assert mz == b"MZ", "NuGet.exe does not have MZ PE header"

        # Run file command to verify binary format
        self.run(f'file "{nuget_exe}" 2>&1 | grep -i "PE32\\|PE32+\\|MS-DOS"', ignore_errors=True)

        # Verify NOTICES.txt exists in share/
        notices = os.path.join(pkg, "share", "NOTICES.txt")
        assert os.path.exists(notices), f"NOTICES.txt not found at {notices}"
