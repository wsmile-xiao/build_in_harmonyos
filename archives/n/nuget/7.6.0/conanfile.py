#!/usr/bin/env python3
"""Conan recipe — nuget 7.6.0 (NuGet Command Line Interface, prebuilt binary)

NuGet.CommandLine is distributed as a .nupkg (ZIP) containing NuGet.exe,
a .NET Framework PE32 executable. This recipe downloads the .nupkg from
nuget.org (official source), extracts NuGet.exe, and packages it with a
wrapper script.

Source: nuget.org (official NuGet Gallery)
License: Apache-2.0

R32: settings.os check uses `in ("Linux", "OHOS")`
R28: test_package/ included
R38: commands.json declared at software level
"""
import os
import stat
import zipfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import download, copy, apply_conandata_patches, export_conandata_patches


class NugetConan(ConanFile):
    name = "nuget"
    version = "7.6.0"
    description = "NuGet Command Line Interface (prebuilt .NET binary)"
    license = "Apache-2.0"
    homepage = "https://aka.ms/nugetprj"
    url = ""  # CI fills this

    # R32: settings.os must check `in ("Linux", "OHOS")`
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def validate(self):
        # R32: OS compatibility check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"nuget does not support OS: {self.settings.os}"
            )

    def source(self):
        # Download the .nupkg (ZIP format) from nuget.org (official source, R39)
        sources = self.conan_data["sources"]
        download(self, url=sources["url"], filename="nuget-7.6.0.nupkg", sha256=sources["sha256"])

    def build(self):
        # Apply patches (none for prebuilt binary, but required by G1 check)
        apply_conandata_patches(self)

        # Extract the .nupkg (it's a ZIP archive)
        with zipfile.ZipFile("nuget-7.6.0.nupkg", "r") as z:
            z.extractall(".")

        # Verify NuGet.exe exists after extraction
        nuget_exe = os.path.join(self.source_folder, "tools", "NuGet.exe")
        if not os.path.exists(nuget_exe):
            raise Exception("NuGet.exe not found in extracted .nupkg")

        # Create wrapper script
        # NuGet.exe is a .NET Framework PE32 binary.
        # On Linux/OHOS it requires mono or a .NET-compatible runtime to execute.
        wrapper_content = (
            "#!/usr/bin/env bash\n"
            "# nuget wrapper — NuGet Command Line Interface\n"
            "# NuGet.exe is a .NET Framework PE32 assembly.\n"
            "# It requires mono or a compatible .NET runtime on Linux/OHOS.\n"
            'NUGET_EXE="$(dirname "$0")/../libexec/NuGet.exe"\n'
            '\n'
            '# Try mono (cross-platform .NET Framework runtime)\n'
            'if command -v mono >/dev/null 2>&1; then\n'
            '    exec mono "$NUGET_EXE" "$@"\n'
            'fi\n'
            '\n'
            '# Try direct execution (Windows/WSL/PE-loader)\n'
            'exec "$NUGET_EXE" "$@"\n'
        )
        wrapper_path = os.path.join(self.source_folder, "nuget")
        with open(wrapper_path, "w") as f:
            f.write(wrapper_content)
        os.chmod(wrapper_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    def package(self):
        # Copy NuGet.exe to libexec/
        copy(self, "NuGet.exe", os.path.join(self.source_folder, "tools"),
             os.path.join(self.package_folder, "libexec"))
        # Copy NuGet.pdb to libexec/ (debug symbols)
        copy(self, "NuGet.pdb", os.path.join(self.source_folder, "tools"),
             os.path.join(self.package_folder, "libexec"))
        # Copy wrapper script to bin/
        copy(self, "nuget", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        # Ensure wrapper is executable
        wrapper_dest = os.path.join(self.package_folder, "bin", "nuget")
        if os.path.exists(wrapper_dest):
            os.chmod(wrapper_dest, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        # Copy NOTICES.txt to share/
        copy(self, "NOTICES.txt", self.source_folder,
             os.path.join(self.package_folder, "share"))

    def package_info(self):
        # This is a CLI tool, not a C/C++ library
        # Set bindirs so the wrapper script is on PATH
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["libexec"]
