#!/usr/bin/env python3
"""Conan recipe — avro-tools 1.12.1 (Java prebuilt JAR).

This is a prebuilt binary package (Java JAR + wrapper script).
No compilation step — just download, create wrapper, and package.

Source: Maven Central (fast CDN download)
License: Apache-2.0

R32: settings.os check uses `in ("Linux", "OHOS")`
R28: test_package/ included
"""
import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import download, copy, apply_conandata_patches, export_conandata_patches


class AvroToolsConan(ConanFile):
    name = "avro-tools"
    version = "1.12.1"
    description = "Apache Avro command-line tools and utilities (prebuilt JAR)"
    license = "Apache-2.0"
    homepage = "https://avro.apache.org/"
    url = ""  # CI fills this

    # R32: settings.os must check `in ("Linux", "OHOS")`
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def validate(self):
        # R32: OS compatibility check — must use `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"avro-tools does not support OS: {self.settings.os}"
            )

    def source(self):
        # Download the JAR file from Maven Central (no extraction needed)
        sources = self.conan_data["sources"]
        download(self, url=sources["url"], filename="avro-tools-1.12.1.jar", sha256=sources.get("sha256"))

    def build(self):
        # Apply patches (none for prebuilt JAR, but required by G1 check)
        apply_conandata_patches(self)

        # Create wrapper script that invokes java -jar
        wrapper_content = (
            "#!/usr/bin/env bash\n"
            "# avro-tools wrapper - Apache Avro command-line tools\n"
            'JAVA_HOME="${JAVA_HOME:-/storage/Users/currentUser/usr/local/bishengjdk17}"\n'
            'exec "$JAVA_HOME/bin/java" -jar "$(dirname "$0")/../libexec/avro-tools-1.12.1.jar" "$@"\n'
        )
        wrapper_path = os.path.join(self.source_folder, "avro-tools")
        with open(wrapper_path, "w") as f:
            f.write(wrapper_content)
        os.chmod(wrapper_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    def package(self):
        # Copy JAR to libexec/
        copy(self, "avro-tools-1.12.1.jar", self.source_folder, os.path.join(self.package_folder, "libexec"))
        # Copy wrapper script to bin/
        copy(self, "avro-tools", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Ensure wrapper is executable
        wrapper_dest = os.path.join(self.package_folder, "bin", "avro-tools")
        if os.path.exists(wrapper_dest):
            os.chmod(wrapper_dest, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    def package_info(self):
        # This is a Java tool, not a C/C++ library
        # Set bindirs so the wrapper script is on PATH
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["libexec"]
